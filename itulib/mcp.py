"""The MCP surface: nine tools, same shape as `rfclib`, pointed at the ITU corpus.

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
import sys

from . import corpus, index, sources, text
from .errata import errata_text

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

    def _fail(error: Exception, hint: str = "") -> str:
        payload = {"error": f"{type(error).__name__}: {error}"}
        if hint:
            payload["hint"] = hint
        return _guard(payload)

    def _target(ref: str, edition: str) -> tuple[sources.Edition, str, int | None]:
        rec, number, para = text.parse_ref(ref)
        return sources.resolve(rec or edition), number, para

    @app.tool(
        description="Full-text clause search, cut to a token budget. `truncated` says whether the budget, not "
        "the corpus, ended the list."
    )
    def itu_search(query: str, edition: str = "X.690", limit: int = 8, max_tokens: int = 1500) -> str:
        try:
            item = sources.resolve(edition)
            hits = index.search(item, query, limit)
        except Exception as error:  # noqa: BLE001 - a crash tells the client nothing at all
            return _fail(error, "python -m itulib.cli sync")
        kept: list[dict[str, str]] = []
        used, truncated = 0, False
        for hit in hits:
            cost = (len(hit.excerpt) + len(hit.title) + 40) // index.CHARS_PER_TOKEN
            if kept and used + cost > max_tokens:
                truncated = True
                break
            used += cost
            kept.append(
                {
                    "ref": f"{item.rec}§{hit.number}",
                    "title": hit.title,
                    "excerpt": hit.excerpt,
                    "cite": index.citation(item, hit.number),
                }
            )
        return _guard({"edition": edition, "query": query, "hits": kept, "truncated": truncated})

    @app.tool(
        description="Read a clause by ref ('X.690§11.6', '11.6', or one sentence 'X.690§11.6¶2'). Long clauses "
        "are paged: pass the returned `next` as `start`. view: text | normative (shall/should/may sentences) | "
        "refs (what it points at and what points at it). ¶n is the nth sentence of the extracted clause."
    )
    def itu_read(
        number: str, edition: str = "X.690", max_tokens: int = 2000, start: int = 1, view: str = "text"
    ) -> str:
        try:
            item, clause_number, para = _target(number, edition)
            if view == "normative":
                found = index.normative_statements(item, clause_number)
                if found is None:
                    return _guard({"error": f"{item.key}: no clause §{clause_number}", "search_instead": True})
                return _guard(
                    {
                        "cite": index.citation(item, clause_number),
                        "statements": [
                            {"para": n, "cite": index.citation(item, clause_number, n), "text": s} for n, s in found
                        ],
                    }
                )
            if view == "refs":
                return itu_links(f"{item.rec}§{clause_number}")
            if para is not None:
                one = index.sentence(item, clause_number, para)
                if one is None:
                    return _guard({"error": f"{item.key}: §{clause_number} has no ¶{para}"})
                return _guard({"cite": index.citation(item, clause_number, para), "text": one})
            page = index.page(item, clause_number, start=start, max_tokens=max_tokens)
        except Exception as error:  # noqa: BLE001 - a crash tells the client nothing at all
            return _fail(error)
        if page is None:
            return _guard({"error": f"{item.key}: no clause §{clause_number}", "search_instead": True})
        result: dict[str, object] = {
            "cite": index.citation(item, page.number),
            "number": page.number,
            "title": page.title,
            "paras": f"{page.first}-{page.last} of {page.total}",
            "text": page.text,
            "next": None if page.next is None else {"start": page.next},
        }
        extra = index.fragments(item, clause_number) - 1
        if extra:
            result["warning"] = (
                f"{extra} other extracted fragment(s) carry the number {clause_number} (a numbered sub-item, "
                "table cell or history row the splitter could not tell from a heading); this is the first. "
                "Check the PDF before relying on it for a normative claim."
            )
        return _guard(result)

    @app.tool(description="The citation string for a clause or sentence, built from the registry: 'X.690§11.6¶2'.")
    def itu_cite(ref: str, edition: str = "X.690") -> str:
        try:
            item, clause_number, para = _target(ref, edition)
            if index.read(item, clause_number) is None:
                return _guard(
                    {"error": f"{item.key}: no clause §{clause_number}; refusing to cite what is not there"}
                )
        except Exception as error:  # noqa: BLE001 - a crash tells the client nothing at all
            return _fail(error)
        return _guard({"cite": index.citation(item, clause_number, para), "digest": item.sha256})

    @app.tool(
        description="References of a clause: same-document clauses it points at, other recommendations, ISO/IEC "
        "and RFC citations, and which clauses of this edition cite it. `unresolved` clause numbers were "
        "pointed at but are not in the index."
    )
    def itu_links(ref: str, edition: str = "X.690") -> str:
        try:
            item, clause_number, _para = _target(ref, edition)
            found = index.links(item, clause_number)
        except Exception as error:  # noqa: BLE001 - a crash tells the client nothing at all
            return _fail(error)
        if found is None:
            return _guard({"error": f"{item.key}: no clause §{clause_number}", "search_instead": True})
        return _guard(
            {
                "cite": index.citation(item, clause_number),
                "points_at": list(found.clauses),
                "unresolved": list(found.unresolved),
                "recommendations": list(found.recommendations),
                "standards": list(found.standards),
                "cited_by": list(found.cited_by),
            }
        )

    @app.tool(
        description="Browse the catalog. No argument: the ITU-T series A-Z and which are registered. A series "
        "letter ('X'): its registered recommendations. A recommendation ('X.690'): its top-level clauses."
    )
    def itu_browse(path: str = "", depth: int = 2) -> str:
        try:
            if not path:
                registered = {item.rec.split(".")[0] for item in sources.IN_FORCE}
                return _guard(
                    [
                        {"series": letter, "title": title, "registered": letter in registered}
                        for letter, title in sources.SERIES.items()
                    ]
                )
            if len(path) == 1:
                return _guard(
                    [
                        {"rec": item.rec, "title": item.title, "fetched": corpus.has(item)}
                        for item in sources.IN_FORCE
                        if item.rec.startswith(path.upper() + ".")
                    ]
                )
            rows = index.top_level(sources.resolve(path), depth)
        except Exception as error:  # noqa: BLE001 - a crash tells the client nothing at all
            return _fail(error, "python -m itulib.cli sync")
        return _guard([{"number": number, "title": title} for number, title in rows])

    @app.tool(description="Clause outline of an edition: numbers and titles, no bodies.")
    def itu_outline(edition: str = "X.690") -> str:
        try:
            rows = index.outline(sources.resolve(edition))
        except Exception as error:  # noqa: BLE001 - a crash tells the client nothing at all
            return _fail(error)
        return _guard([{"number": number, "title": title} for number, title in rows])

    @app.tool(
        description="Regex over clause bodies, one pass, excerpts around the match, cut to a token budget. "
        "`truncated` says the budget, not the corpus, ended the list."
    )
    def itu_grep(pattern: str, edition: str = "X.690", max_tokens: int = 1500) -> str:
        try:
            hits, truncated = index.grep(sources.resolve(edition), pattern, max_tokens=max_tokens)
        except Exception as error:  # noqa: BLE001 - a crash tells the client nothing at all
            return _fail(error)
        return _guard({"pattern": pattern, "hits": hits, "truncated": truncated})

    @app.tool(description="Errata, amendments and corrigenda registered against an edition.")
    def itu_errata(rec: str = "X.690") -> str:
        items = [item for item in sources.AMENDMENTS if item.rec == rec]
        rows: list[dict[str, object]] = []
        for item in items:
            row: dict[str, object] = {"key": item.key, "label": item.label, "status": item.status}
            if item.artifact:
                row["fetched"] = corpus.has(item)
                if row["fetched"]:
                    row["text"] = errata_text(item)
                else:
                    row["hint"] = f"python -m itulib.cli fetch {item.key}"
            rows.append(row)
        return _guard(
            {
                "rec": rec,
                "items": rows,
                "caveat": next((item.note for item in items if item.note), ""),
            }
        )

    return app


def main() -> None:
    import anyio

    anyio.run(build().run_stdio_async)  # type: ignore[attr-defined]


if __name__ == "__main__":
    # stderr, never stdout. stdout *is* the protocol: a friendly notice printed there arrives before the
    # handshake and the client fails with "Failed to parse JSONRPC message from server", naming neither the
    # line nor the reason. The stdio test caught this; importing the module never would.
    print("itulib: speaking MCP on stdio; run it from a client, not a terminal", file=sys.stderr)
    main()
