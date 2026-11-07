# itulib

ITU-T recommendations as a **local, citation-precise library and MCP server**. It starts with the ASN.1 family
(X.680-X.697): the normative source for ASN.1 and for the BER, CER, DER and PER encoding rules, none of which is
in the RFC series, so an RFC-only tool such as `rfclib` cannot answer "what does X.690 actually say?".

```
pip install "itulib[mcp]"
itulib sync                      # fetch + index the 12 ASN.1 recommendations into ~/.itulib (about 14 MB)
itulib search X.690 set-of order
itulib read X.690§11.6
itulib cite X.690§11.6¶2         # Rec. ITU-T X.690 (02/2021) §11.6¶2
```

## The text is not in this package

ITU reserves all rights in its recommendations and permits no reproduction without written permission. So
`itulib` ships **code, a registry of editions with pinned digests, and tests that pass with no corpus present**.
`itulib fetch` / `itulib sync` download the PDFs from itu.int onto *your* machine (`$ITULIB_HOME`, default
`~/.itulib`), check each against its pinned SHA-256, and refuse a mismatch instead of silently citing different
text. Nothing is ever written into a checkout or a site-packages directory. See `NOTICE`.

## Use it from an AI client (MCP)

```
claude mcp add --scope user itulib -- itulib mcp
```

or, for any MCP client, a stdio server running `itulib mcp`. If the extra is missing, `itulib mcp` exits with
status 2 and tells you to install `itulib[mcp]`.

| Tool | What it does |
|---|---|
| `itu_search` | full-text clause search, token-budgeted; `relaxed` says only some terms matched |
| `itu_read` | read a clause, one sentence (`X.690§11.6¶2`), the `normative` statements, or the `refs`; long clauses page via `next` |
| `itu_cite` | the citation string, built from the registry; refuses to cite a clause that is not there |
| `itu_links` | clauses this one points at, other recommendations and standards, and what cites it |
| `itu_browse` | ITU-T series A-Z, a series' registered recommendations, a recommendation's top-level clauses |
| `itu_outline` | paged clause outline with `prefix` and `depth` |
| `itu_grep` | regex over clause bodies with excerpts, token-budgeted |
| `itu_errata` | errata and amendments registered for a recommendation, with the erratum text once fetched |
| `itu_info` | registered editions, digests and what is fetched (needs no corpus) |

It also serves `itu://{rec}/{number}` as a resource template and two prompts, `explain_clause` and
`verify_claim`.

**Error semantics.** A missing corpus or index returns an `error` object naming the command that fixes it, never
an empty list: an empty `hits` always means no clause matched.

## References and citations

One grammar everywhere: `X.690§11.6`, `X.690§11.6¶2`, or the looser `X.690 11.6` / `11.6` (which means X.690).
Annex clauses work too (`X.690§A.1`). **`¶n` is the nth sentence of the extracted clause, not ITU's own
paragraph numbering**: PDF extraction flattens paragraph structure, so a `¶` citation should travel with the
clause number and edition, which `cite` always gives.

## What is covered

All twelve are the 02/2021 edition, in force at the time of writing: X.680, X.681, X.682, X.683, X.690, X.691,
X.692, X.693, X.694, X.695, X.696, X.697, plus X.690 Erratum 1 (09/2021). `itulib browse` lists the full ITU-T
series index (A-Z); only the ASN.1 recommendations are registered so far.

## Known limits

- The PDFs are segmented into clauses by heuristics, not from ITU's own structure. Pointer text ("see 8.1.2"),
  the document-history table and contents lines are filtered, but a few clause numbers still map to more than one
  extracted fragment (history tables, numbered sub-items); `itu_read` returns the first and says so in a
  `warning`. **Check the PDF before relying on a clause for a normative claim.**
- Heading-only clauses ("8.1.2 Identifier octets") have no text of their own; reading one lists its subclauses.
- Figures and tables do not survive extraction. Erratum 1 to X.690, for instance, replaces a figure.
- Search is keyword (SQLite FTS5, porter stemming) with an any-term fallback. There is no semantic search.
- Only the in-force editions are indexed; superseded editions are registered but not extracted.

## Development

```
python -m pip install -e ".[dev]"
python -m pytest -q          # passes with no corpus present, by design
python -m ruff check . && python -m ruff format --check . && python -m mypy itulib tests
```

`tests/test_license.py` fails if ITU text, a PDF, or a verbatim clause sentence ever appears in the tree, and
if any other test requires the corpus.
