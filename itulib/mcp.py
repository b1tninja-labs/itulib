"""The MCP surface: six tools, same shape as `rfclib`, pointed at the ITU corpus.

Two deliberate behaviours, both learned the hard way elsewhere in this portfolio.

A missing corpus returns an **error object naming the command**, never an empty list. `sync_roadmap.graphql()`
used to swallow a scope failure into `""`, which its caller rendered as "the board has no issues"; a tool that
answers "no clauses match" when the real state is "the corpus is not installed" is the same bug wearing a
different hat.

The import lives inside `build()` because `mcp` 2.x renamed `FastMCP` to `MCPServer` and every example online
still uses the old name, so the failure mode is a client that reports only that the server did not start.
Importing lazily also keeps the library usable without the MCP extra installed.
"""

from __future__ import annotations

import json

from . import corpus, index, sources

INSTRUCTIONS = (
    "ITU-T recommendations (X.680, X.690) as clause-precise search and citation. The corpus is fetched by the "
    "user and is never shipped with this package. Always cite by edition and subclause, e.g. "
    "Rec. ITU-T X.690 (02/2021) §11.1. An empty result means no clause matched; an 'error' field means the "
    "corpus is missing and says which command installs it."
)


def _guard(action: object) -> str:
    try:
        return json.dumps(action, indent=2)
    except TypeError:  # pragma: no cover - defensive
        return json.dumps({"rendered": str(action)})


def build() -> object:
    from mcp.server.mcpserver import MCPServer

    app = MCPServer(name="itulib", instructions=INSTRUCTIONS)

    @app.tool(description="Registered editions, their status, digests and amendments. No corpus needed.")
    def itu_info(rec: str = "") -> str:
        pool = [item for item in (*sources.IN_FORCE, *sources.SUPERSEDED) if not rec or item.rec == rec]
        return _guard(
            {
                "editions": [
                    {
                        "key": item.key,
                        "status": item.status,
                        "edition": item.edition,
                        "octets": item.octets,
                        "sha256": item.sha256 or None,
                        "fetched": corpus.has(item),
                        "note": item.note,
                    }
                    for item in pool
                ],
                "amendments": [
                    {"key": item.key, "label": item.label, "status": item.status, "note": item.note}
                    for item in sources.AMENDMENTS
                    if not rec or item.rec == rec
                ],
                "corpus_home": str(corpus.home()),
            }
        )

    @app.tool(description="Full-text clause search. Returns clause numbers, titles and excerpts.")
    def itu_search(query: str, edition: str = "X.690", limit: int = 8) -> str:
        try:
            hits = index.search(sources.resolve(edition), query, limit)
        except (corpus.CorpusMissing, KeyError, RuntimeError) as error:
            return _guard({"error": str(error), "hint": "python -m itulib.cli fetch && python -m itulib.cli index"})
        return _guard(
            {
                "edition": edition,
                "query": query,
                "hits": [{"number": hit.number, "title": hit.title, "excerpt": hit.excerpt} for hit in hits],
            }
        )

    @app.tool(description="One clause, verbatim from the fetched edition, with its citation.")
    def itu_read(number: str, edition: str = "X.690") -> str:
        try:
            item = sources.resolve(edition)
            clause = index.read(item, number.lstrip("§"))
        except (corpus.CorpusMissing, KeyError, RuntimeError) as error:
            return _guard({"error": str(error)})
        if clause is None:
            return _guard({"error": f"{edition}: no clause §{number}", "search_instead": True})
        return _guard({"cite": clause.cite(item.key), "number": clause.number, "text": clause.body})

    @app.tool(description="Clause outline of an edition: numbers and titles, no bodies.")
    def itu_outline(edition: str = "X.690") -> str:
        try:
            rows = index.outline(sources.resolve(edition))
        except (corpus.CorpusMissing, KeyError, RuntimeError) as error:
            return _guard({"error": str(error)})
        return _guard([{"number": number, "title": title} for number, title in rows])

    @app.tool(description="Regex over clause bodies. Each hit carries its clause number.")
    def itu_grep(pattern: str, edition: str = "X.690") -> str:
        import re

        try:
            rows = index.outline(sources.resolve(edition))
            item = sources.resolve(edition)
            found = []
            for number, _title in rows:
                clause = index.read(item, number)
                if clause and re.search(pattern, clause.body, re.I):
                    found.append({"number": number, "excerpt": clause.body[:400]})
        except (corpus.CorpusMissing, KeyError, RuntimeError) as error:
            return _guard({"error": str(error)})
        return _guard({"pattern": pattern, "hits": found[:20]})

    @app.tool(description="Errata, amendments and corrigenda registered against an edition.")
    def itu_errata(rec: str = "X.690") -> str:
        items = [item for item in sources.AMENDMENTS if item.rec == rec]
        return _guard(
            {
                "rec": rec,
                "items": [{"key": item.key, "label": item.label, "status": item.status} for item in items],
                "caveat": next((item.note for item in items if item.note), ""),
            }
        )

    return app


def main() -> None:
    import anyio

    anyio.run(build().run_stdio_async)  # type: ignore[attr-defined]


if __name__ == "__main__":
    print("itulib: speak MCP on stdio; run it from a client, not a terminal")
    main()
