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
from dataclasses import asdict

from . import __version__, corpus, index, sources, text
from .errata import errata_text

INSTRUCTIONS = (
    "ITU-T recommendations (the ASN.1 family X.680-X.697) as clause-precise search and citation. The corpus is "
    "fetched by the user and never shipped with this package. Refs look like X.690§11.6 or X.690§11.6¶2, where "
    "¶n is the nth sentence of the extracted clause. Cite with the `cite` string a tool returns, e.g. "
    "Rec. ITU-T X.690 (02/2021) §11.6. Long results are paged: pass `next.start` back as `start`. "
    "An empty `hits` list means no clause matched; an `error` field means the corpus or index is missing and "
    "names the command that fixes it; `relaxed` means only some search terms matched; `warning` means the "
    "clause number is ambiguous in the extracted text, so check the PDF before relying on it."
)


def _guard(action: object) -> str:
    """Serialise a tool result compactly.

    These results are read by a model, so every character is a token's worth of cost. Indentation and escaped
    non-ASCII ("\u00a7" for the section sign, six characters instead of one) were about a fifth of a typical
    search or outline response; the JSON is otherwise unchanged and parses identically.
    """
    try:
        return json.dumps(action, separators=(",", ":"), ensure_ascii=False)
    except TypeError:  # pragma: no cover - defensive
        return json.dumps({"rendered": str(action)}, separators=(",", ":"), ensure_ascii=False)


def build() -> object:
    from mcp.server.mcpserver import MCPServer

    app = MCPServer(name="itulib", instructions=INSTRUCTIONS, version=__version__)

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
            hits, relaxed = index.search_mode(item, query, limit)
        except Exception as error:  # noqa: BLE001 - a crash tells the client nothing at all
            return _fail(error, "itulib sync")
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
                    "match": "all terms" if hit.all_terms else "some terms",
                }
            )
        result: dict[str, object] = {"edition": edition, "query": query, "hits": kept, "truncated": truncated}
        if relaxed:
            result["relaxed"] = (
                "fewer clauses contain every term than requested; hits marked 'some terms' match part of the query"
            )
        return _guard(result)

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
        if page is None or page.total == 0:
            kids = index.children(item, clause_number)
            if kids:
                return _guard(
                    {
                        "cite": index.citation(item, clause_number),
                        "note": "heading only: this clause has no text of its own; read a subclause",
                        "subclauses": [{"number": n, "title": t} for n, t in kids],
                    }
                )
            if page is None:
                return _guard({"error": f"{item.key}: no clause §{clause_number}", "search_instead": True})
            return _guard(
                {
                    "cite": index.citation(item, clause_number),
                    "title": page.title,
                    "note": "heading with no text of its own and no indexed subclauses",
                }
            )
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
    def itu_browse(path: str = "", depth: int = 2, start: int = 0, max_tokens: int = 1500) -> str:
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
            shown, more = index.slice_rows(index.top_level(sources.resolve(path), depth), start, max_tokens)
        except Exception as error:  # noqa: BLE001 - a crash tells the client nothing at all
            return _fail(error, "itulib sync")
        return _guard(
            {
                "items": [{"number": n, "title": t} for n, t in shown],
                "next": None if more is None else {"start": more},
            }
        )

    @app.tool(
        description="The ITU-T catalogue read from itu.int by `itulib catalog sync`: in-force editions and the "
        "formats each is offered in (PDF, EPB=EPUB, MSW=Word, TOC-HTM, SUM-HTM; '*' marks not freely available). "
        "Metadata only. Paged: pass `next.start` back as `start`."
    )
    def itu_catalog(
        series: str = "X", text: str = "", fmt: str = "", free: bool = False, start: int = 0, max_tokens: int = 1500
    ) -> str:
        from . import catalog

        try:
            recs = catalog.load(series.upper())
            found = catalog.rows(recs, text=text, fmt=fmt, free_only=free)
            shown, more = index.slice_rows(
                tuple((f"{r.rec} {r.label}", f"{r.summary()} {r.title}") for r in found),
                start,
                max_tokens,
            )
        except Exception as error:  # noqa: BLE001 - a crash tells the client nothing at all
            return _fail(error, f"itulib catalog sync {series.upper()} --details")
        detailed = sum(1 for entry in recs.values() if entry.get("components") is not None)
        return _guard(
            {
                "series": series.upper(),
                "total": len(found),
                "recommendations_with_details": f"{detailed} of {len(recs)}",
                "items": [asdict(found[start + i]) for i in range(len(shown))],
                "next": None if more is None else {"start": more},
            }
        )

    @app.tool(
        description="Compare one clause between two editions, by sentence: what was removed and what was added. "
        "Numbering can differ between editions, so a clause missing from one edition may have moved, not gone."
    )
    def itu_compare(
        number: str, edition_a: str = "X.690#2008-11", edition_b: str = "X.690#2021-02", max_tokens: int = 2000
    ) -> str:
        try:
            first, second = sources.resolve(edition_a), sources.resolve(edition_b)
            _rec, clause_number, _para = text.parse_ref(number)
            result = index.compare(first, second, clause_number)
        except Exception as error:  # noqa: BLE001 - a crash tells the client nothing at all
            return _fail(error, "itulib sync --all")
        budget = max(max_tokens, 1) * index.CHARS_PER_TOKEN
        out: dict[str, object] = {
            "a": index.citation(first, clause_number),
            "b": index.citation(second, clause_number),
            "in_a": result.in_a,
            "in_b": result.in_b,
            "same": result.same if result.in_a and result.in_b else None,
        }
        for key, rows in (("removed_from_a", result.removed), ("added_in_b", result.added)):
            kept: list[dict[str, object]] = []
            used = 0
            for para, sentence in rows:
                if kept and used + len(sentence) > budget:
                    out["truncated"] = True
                    break
                used += len(sentence)
                kept.append({"para": para, "text": sentence})
            out[key] = kept
        return _guard(out)

    @app.tool(
        description="Clause outline of an edition: numbers and titles, no bodies. Paged: pass `next.start` back "
        "as `start`. `prefix` limits it to one subtree ('8.1'); `depth` caps the numbering depth (0 = all)."
    )
    def itu_outline(
        edition: str = "X.690", prefix: str = "", depth: int = 0, start: int = 0, max_tokens: int = 1500
    ) -> str:
        try:
            rows = index.outline(sources.resolve(edition))
            if prefix:
                rows = tuple(r for r in rows if r[0] == prefix or r[0].startswith(prefix + "."))
            if depth:
                rows = tuple(r for r in rows if r[0].count(".") + 1 <= depth)
            shown, more = index.slice_rows(rows, start, max_tokens)
        except Exception as error:  # noqa: BLE001 - a crash tells the client nothing at all
            return _fail(error)
        return _guard(
            {
                "total": len(rows),
                "items": [{"number": n, "title": t} for n, t in shown],
                "next": None if more is None else {"start": more},
            }
        )

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
                    row["hint"] = f"itulib fetch {item.key}"
            rows.append(row)
        return _guard(
            {
                "rec": rec,
                "items": rows,
                "caveat": next((item.note for item in items if item.note), ""),
            }
        )

    @app.resource(
        "itu://{rec}/{number}",
        name="clause",
        description="One clause as text with its citation, e.g. itu://X.690/11.6",
        mime_type="text/plain",
    )
    def clause_resource(rec: str, number: str) -> str:
        item = sources.resolve(rec)
        page = index.page(item, number, max_tokens=4000)
        if page is None:
            raise ValueError(f"{item.key}: no clause §{number}")
        return f"{index.citation(item, page.number)}\n\n{page.text}"

    @app.prompt(description="Explain a clause in plain language, grounded in and cited to the fetched text.")
    def explain_clause(ref: str) -> str:
        return (
            f"Explain {ref} in plain language. Call itu_read for the clause (page it if `next` is set), and "
            "itu_links to find the clauses it depends on and read those too. Quote nothing you did not read "
            "from a tool result, and cite every statement with the `cite` string the tools return, including "
            "the ¶ number for sentences. If a tool returns an error or a `warning`, say so instead of filling "
            "the gap from memory."
        )

    @app.prompt(description="Check a claim about an encoding rule against the text, with citations.")
    def verify_claim(claim: str, rec: str = "X.690") -> str:
        return (
            f"Verify this claim against {rec}: {claim}\n\n"
            "Use itu_search (and itu_grep for exact wording), read each candidate clause with itu_read, and "
            "use view=normative to separate obligations from notes. Answer SUPPORTED, CONTRADICTED or NOT "
            "FOUND, cite the clause and edition for each, and check itu_errata for a correction to the cited "
            "text. NOT FOUND means no clause says it; it is not evidence the claim is true or false. Do not "
            "answer from memory."
        )

    return app


def require_extra() -> None:
    """Raise ImportError naming the extra if the MCP SDK is not installed. Checked before anything is served, so
    a missing extra is one clear sentence and exit status 2, never a traceback from deep inside the SDK."""
    try:
        import anyio  # noqa: F401
        from mcp.server.mcpserver import MCPServer  # noqa: F401
    except ImportError as error:
        raise ImportError(f"itulib mcp needs the MCP extra: pip install 'itulib[mcp]' ({error})") from error


def main() -> None:
    require_extra()
    import anyio

    anyio.run(build().run_stdio_async)  # type: ignore[attr-defined]


if __name__ == "__main__":
    # stderr, never stdout. stdout *is* the protocol: a friendly notice printed there arrives before the
    # handshake and the client fails with "Failed to parse JSONRPC message from server", naming neither the
    # line nor the reason. The stdio test caught this; importing the module never would.
    print("itulib: speaking MCP on stdio; run it from a client, not a terminal", file=sys.stderr)
    main()
