# Instructions for coding agents

`itulib` answers one question: what does a clause of an ITU-T recommendation say, and where is it. It exists
because X.680 and X.690 are normative for BER and DER and are **not in the RFC series**, so `rfclib` cannot
reach them. The corpus is fetched by the user and never committed.

## Commands

```
python -m pip install -e ".[dev]"
python -m itulib.cli info                  # registry: editions, digests, what is fetched — no corpus needed
python -m itulib.cli fetch X.690           # network; writes to ITULIB_HOME, never here
python -m itulib.cli index X.690
python -m itulib.cli search X.690 "BOOLEAN"
python -m itulib.cli read X.690 11.1
python -m pytest -q                        # passes with no corpus present, by design
python -m ruff check .
python -m ruff format --check .
python -m mypy itulib tests
```

Python 3.12+: `from __future__ import annotations`, `collections.abc`, `X | None`, `datetime.UTC`. `ruff format`
decides line breaks. Never run a formatter from above this directory.

## The two rules that define this repository

**Never put ITU text in the tree.** Not the PDF, not a vendored extract, not one clause pasted into a docstring
or a fixture to make a test pass. ITU reserves all rights and permits no reproduction without written
permission; `tests/test_license.py` enforces the easy versions of this and is not a proof, so read it before
deciding a paraphrase is harmless. Tests must run without the corpus — a suite that skips quietly reports the
same green as one that ran.

**Never answer from memory.** The reason this repository exists is that `VECTORS.md` once asserted an OID arc
was illegal and was wrong. A citation is `Rec. ITU-T X.690 (02/2021) §n.n` produced from a fetched, digest-
matched edition. If the corpus is absent, say so and name the command; an empty list must mean "no clause
matches", never "the file was not there". `sources.py` digests are pinned from bytes actually downloaded — if
ITU republishes, the fetch fails loudly rather than silently citing different text.

## MCP

`python -m itulib.mcp` serves six tools (`itu_info`, `itu_search`, `itu_read`, `itu_outline`, `itu_grep`,
`itu_errata`). Register it in `~/.cline/data/settings/cline_mcp_settings.json` as a stdio server. The import is
`from mcp.server.mcpserver import MCPServer` — **mcp 2.x renamed `FastMCP` to `MCPServer`**, every example
online still says the old name, and the failure mode is a client reporting only that the server did not start.

## Where the questions come from

`asn1core/VECTORS.md` rows marked `[verify against X.690]` and `[verify against X.680]`, listed with their
status in `PLAN.md` §3. Retiring a marker means editing `asn1core` with the citation attached; recording where
a clause lives is not the same as resolving the row.
