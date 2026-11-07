# itulib roadmap

The obligation list for reaching the encoding-rule text: every question the portfolio has that `rfclib`
cannot answer, with an honest status against this tree. Same rule as every other matrix here — **a row reads
`[ok]` only when a named test would fail if the behaviour regressed.** For this project that rule has a sharp
edge: the corpus cannot be in CI, so any row whose truth depends on the real PDF cannot read `[ok]`, only
`[part]` with the gap named. A row that quietly becomes `[ok]` because a test exists for the wrapper and not
for the claim is the exact failure this document exists to prevent.

Legend: `[ok]` implemented and pinned by a named test -- `[part]` partial, with what is missing stated --
`[ ]` not implemented -- `[no]` deliberate non-goal.

## 1. Reaching the text

| Obligation | Spec | Status | Where |
|---|---|---|---|
| `ia.sources_registry` | PLAN.md §1 | `[ok]` | `tests/test_sources.py::test_in_force_editions_are_pinned_and_sized`, `test_resolve_refuses_to_guess` — digests and sizes pinned from bytes measured 2026-11-07 |
| `ia.fetch_verify` | ITU `dologin_pub.asp` PDF path | `[part]` | `itulib/corpus.py` — verified live (840,764 B and 2,088,934 B, digests matched, into `~/.itulib`). Cannot be a CI test: it is a network fetch of licensed text, so the digest check goes unexercised after the session that ran it |
| `ia.clause_split` | numbered subclause headings | `[ok]` | `tests/test_text.py::test_real_clauses_are_found_with_their_numbers`, `test_dot_leaders_are_dropped_rather_than_indexed`, `test_bodyless_headings_are_not_indexed` |
| `ia.fts_query` | FTS5 MATCH syntax | `[ok]` | `tests/test_text.py::test_hyphenated_queries_survive_the_search_sanitiser` — found live: `set-of value order` raised `OperationalError` and crashed the MCP tool, because FTS5 reads a hyphen as NOT |
| `ia.index_digest_staleness` | index carries the PDF sha256 | `[part]` | `itulib/index.py::_open` refuses to serve when the corpus no longer matches the index. Verified by hand only; no in-repo test, because building an index needs the corpus, which `tests/test_license.py` forbids |
| `ia.mcp_stdio` | MCP over stdio | `[part]` | `itulib/mcp.py` — driven with a real client: handshake `protocol 2025-11-25`, six tools, search/read/errata answered. **First launch failed**: the `__main__` notice printed to stdout and corrupted the JSON-RPC stream. Fixed; the missing piece is an in-repo smoke test over a synthetic corpus |
| `ia.missing_corpus_not_empty` | error, not empty result | `[ok]` | registry errors return an object naming the remedy (`test_resolve_refuses_to_guess`); same shape for a corpus never fetched. The bug guarded against is `sync_roadmap.graphql()` swallowing a scope failure into `""` |
| `ia.erratum_artefact_ids` | X.690 (2021) Erratum 1 (09/21) | `[ ]` | listed In force, download id unknown: `!!ERSN1-E` and `!!DOC-E` return HTTP 500 and the X.680–X.693 Word zip redirects to a `choice_pub.asp` interstitial. Until the real ids are read off the component page, `itu_errata` can name the erratum but cannot show its text |

## 2. Retiring asn1core's markers

`asn1core/VECTORS.md` marks rows `[verify against X.690]` when a rule came from memory, and one remembered
rule (an illegal OID arc) was already wrong. Each row was queried against the fetched 02/2021 text. The work
lives *in asn1core* — a citation attached to the row and a check of the implementation — so every row here
stays `[ ]` until that commit exists. Recording where a clause is is not retiring a marker.

| Obligation | Clause found | Status | Where |
|---|---|---|---|
| `ia.retire_setof_unsorted` | §11.6 with §10.1 | `[ ]` | `asn1core/VECTORS.md`, `asn1core/der.py::check_set_of`. **No defect, and the reason is the finding.** §11.6 pads the shorter encoding with zero octets for comparison only; §10.1 forces definite, minimally-encoded lengths, so two distinct DER TLVs can never stand in a prefix relation, padding cannot change any comparison, and byte-wise `sorted()` is correct. The row should cite both, and note that BER indefinite-length children are where padding would matter — and those are not DER |
| `ia.retire_bool_nonzero` | §8.2.1–8.2.2 against §11.1 | `[ ]` | BER allows any non-zero contents octet for TRUE, §11.1 narrows it to all-ones under CER/DER. Matches `der.py::check_boolean` as written |
| `ia.retire_int_nonmin` | §8.3.1–8.3.3 | `[ ]` | minimality stated with its rationale. Matches `der.py::check_integer` |
| `ia.repoint_time_leap_second` | §11.7/§11.8 defer the alphabet to X.680 | `[ ]` | **the marker is on the wrong document.** X.690 fixes the form and says nothing about a seconds value of 60 (searched, no match). Re-point at X.680 and re-ask there; RFC 5280 §4.1.2.5.1 stays with `rfclib` |
| `ia.retire_oid_first_arc` | §8.19.1–8.19.2 | `[ ]` | clause located; the two-arc combination subclause still needs quoting, which matters most here because this is the row a remembered answer got wrong |
| `ia.charsets_from_x680` | X.680 restricted alphabets | `[ ]` | X.680 fetched and indexed (856 clauses); no charset question posed or answered yet |
| `ia.set_vs_setof` | §9.3/§10.3 by tag, §11.6 by encoding | `[ ]` | two rules the current prose collapses into "SET OF is sorted". Belongs beside `check_set_of` in asn1core |

## 3. Deliberate non-goals

| Obligation | Spec | Status | Where |
|---|---|---|---|
| `ia.vendor_the_corpus` | ITU rights notice, page iii | `[no]` | no ITU text in the tree, ever. `tests/test_license.py` guards the easy version and states its own limits; the tempting fix for a failing search test is committing the PDF, and history cannot walk that back |
| `ia.a_second_validator` | DER conformance | `[no]` | itulib answers what a clause says; `asn1core` decides what to accept and `VECTORS.md` stays the exit test |
| `ia.rfclib_overlap` | RFC series | `[no]` | RFC questions go to `rfclib`, which owns that corpus and its errata. This exists only for what is not in the RFC series |
| `ia.ocr_scanned_editions` | superseded editions | `[no]` | lineage registered but not extracted; nothing asks a question of a superseded edition, and unverified OCR of licensed text is worse than none |

## 4. Board projection

Nothing here is on Project V2 #2 "Protocol SDK portfolio", and that is not an oversight: **`itulibrary` has no
GitHub remote**, so `sync_roadmap.py` has nowhere to file. Neither does `asn1core`. `git push` there fails with
wording about the repository existing, which is the honest signal that no remote is configured rather than a
permission problem. Creating the repositories is the owner's decision; once one exists,
`py sdk-forge/sync_roadmap.py --project itulibrary --apply --board` projects this matrix and the four-repository
board becomes five.
