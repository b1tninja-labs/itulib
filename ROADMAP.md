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
| `ia.index_digest_staleness` | index carries the PDF sha256 | `[ok]` | `tests/test_index_and_mcp.py::test_index_refuses_to_serve_after_the_corpus_changes`, `test_a_missing_index_is_an_error_not_an_empty_result`, `test_an_extractor_that_finds_nothing_refuses_to_write_an_index` — over invented text and a stand-in file, since the index only hashes the bytes |
| `ia.mcp_stdio` | MCP over stdio | `[ok]` | `tests/test_index_and_mcp.py::test_mcp_stdio_handshake_lists_six_tools_and_reports_a_missing_corpus` drives the real server over stdio (the stdout-notice bug fails it at the handshake) and checks that a missing corpus is an error object. Clause answers from the real PDF are still verified by hand only |
| `ia.missing_corpus_not_empty` | error, not empty result | `[ok]` | registry errors return an object naming the remedy (`test_resolve_refuses_to_guess`); same shape for a corpus never fetched. The bug guarded against is `sync_roadmap.graphql()` swallowing a scope failure into `""` |
| `ia.erratum_artefact_ids` | X.690 (2021) Erratum 1 (09/21) | `[part]` | id found on the erratum's own page (`T-REC-X.690-202109-I!Err1!PDF-E`, not the guessed `!!ERSN1-E`); fetched live, 194,138 B matching ITU's listing, digest pinned. `tests/test_sources.py::test_every_amendment_with_a_download_id_is_pinned`, `test_resolve_document_finds_an_erratum_and_still_refuses_to_guess`. Gaps: the fetch itself is unexercised in CI, and the note is a one-page covering note that replaces Figure 4 (high-tag-number identifier octets) with a picture, so the extract names the correction but cannot show the corrected octets; the PDF is the authority. Amendment 2 (06/06) still has no id |
| `ia.catalog_asn1` | X.680-X.697 in force | `[part]` | twelve editions registered with digests measured 2026-11-07 (`tests/test_sources.py` pins shape and uniqueness); `itulib sync` fetched and indexed all twelve live. The fetch is unexercised in CI. Joint ISO/IEC designations deliberately not recorded: not verified |
| `ia.catalog_x500` | X.500-series in force | `[part]` | twelve editions registered 2026-11-07, each id read off its ITU component page, size matched to the page's listing and digest pinned: X.500, X.501, X.509, X.511, X.518, X.519, X.520, X.521, X.525 (10/2019), X.508 (10/2024), X.510 (10/2023), X.530 (11/2008); plus twelve in-force amendments/corrigenda, pinned and readable as flat text only (`tests/test_sources.py::test_x500_family_is_registered_and_the_restricted_one_is_not`, `test_every_amendment_belongs_to_a_registered_recommendation`, `test_prepublished_amendments_are_not_pinned`). Segmentation measured by `scripts/measure_segmentation.py` (not CI), bookmark headings located / listed, duplicate numbers: X.500 63/63, 0; X.501 388/388, 0; X.508 334/336, 2; X.509 364/364, 0 (389 clauses); X.510 268/268, 0; X.511 182/182, 0; X.518 283/283, 0; X.519 241/241, 0; X.520 279/279, 1; X.521 80/80, 0; X.525 93/93, 0; X.530 43/44, 0. Gaps: **not registered** X.506 (07/2026, prepublished, TIES-only), X.510 Amendment 1 (07/2026, same) and X.509 Corrigendum 3 (07/2026, prepublished; `dologin_pub.asp` returns a login page, only `dologin.asp` serves the PDF, and a prepublished text may still change); X.581-X.586 are withdrawn; X.590 (JSON signature scheme) is in force but not part of the Directory and not registered. Amendments are not applied to the base editions or indexed, so a clause of X.509 (2019) can be superseded by Cor. 1/2 or Amd. 1 without the clause read showing it. Annex module headings (X.509 §A.1) carry the module text as their title; the fetch is unexercised in CI; joint ISO/IEC 9594 designations not recorded (the ITU pages do not state them) |
| `ia.series_index` | ITU-T series A-Z | `[part]` | `sources.SERIES` and `itu_browse`; titles copied from ITU's index page, L truncated there and left truncated. Only the ASN.1 and X.500 recommendations are registered |
| `ia.paging` | rfclib `read` paging | `[ok]` | `tests/test_navigation.py::test_paging_follows_next_and_loses_nothing`, `test_a_page_always_makes_progress_even_if_one_sentence_exceeds_the_budget`. Unit is the **sentence**, not ITU paragraphing: extraction flattens it, so `¶n` is the nth sentence of the extracted clause |
| `ia.budgets` | token-bounded search/grep | `[ok]` | `test_grep_is_budgeted_and_says_when_it_stopped`; `itu_search` budgets the same way but has no direct test |
| `ia.refs_links_cite` | rfclib `links`/`cite`/refs | `[part]` | `test_refs_need_an_introducing_word...`, `test_links_resolve_and_report_back_references`, `test_citation_comes_from_the_registry`. Recall unmeasured: only references introduced by "clause", "subclause" or the section sign are followed |
| `ia.normative_view` | rfclib `view=normative` | `[part]` | `test_normative_picks_obligation_sentences_only`; counts "may", so permissions appear beside obligations |
| `ia.clause_splitter_fidelity` | clauses from the document's own structure | `[part]` | bookmark-guided: `test_listed_headings_give_exact_titles_and_keep_heading_only_parents`, `test_numbered_paragraphs_are_accepted_only_as_successors`, `test_a_pointer_that_matches_a_listed_number_is_not_its_heading`, `test_headings_fall_back_to_contents_lines_when_there_are_no_bookmarks`. Measured on the real PDFs (not CI): 99.8% of 1,261 listed headings located, 0 duplicate numbers except X.692 (11). The numbered paragraphs below the bookmarks are inferred from sequence and unmeasured; figures and tables are lost |
| `ia.running_lines` | page headers/footers out of clause text | `[ok]` | `test_running_headers_and_footers_are_stripped_but_repeated_words_are_not`, `test_repeated_numbered_headings_are_not_running_text` (the second is a regression: X.693 lost 23 headings to the first version of the filter) |
| `ia.superseded_editions` | X.690 2008-11, 2015-08 | `[part]` | registered with digests, fetched and indexed; base texts only (corrigenda not applied). The old `-I` ids returned 'Document Not Found'; superseded editions use `-S` |
| `ia.compare_editions` | `itulib compare` / `itu_compare` | `[part]` | tested only through index-level synthetic text via the sentence matcher in `index.compare`; the real 2008-vs-2021 run reports 23 of 245 shared clauses differing, spot-checked, and ignores symbol-only changes |
| `ia.retrieval_eval` | hit@k / MRR | `[part]` | `scripts/eval_retrieval.py`, 18 cases, hit@1 15/18, hit@5 18/18, MRR 0.900. The expectations were set after seeing early results, so these numbers are optimistic; it is a regression guard, not an unbiased benchmark |
| `ia.heading_only_parents` | read "8.1.2" | `[ok]` | `test_heading_only_parents_expose_their_children` |
| `ia.search_relaxed` | any-term fallback | `[ok]` | `test_search_relaxes_to_any_term_and_says_so`. Ranking of the fallback is bm25 over OR-ed terms: "OBJECT IDENTIFIER first arc" ranks relative-OID clauses above 8.19; unmeasured beyond spot checks |
| `ia.outline_budget` | paged outline/browse | `[ok]` | `test_slice_rows_pages_without_loss_and_always_progresses`; X.692 outline 51k tokens -> 2k per page |
| `ia.packaging` | wheel + sdist | `[part]` | built, `twine check --strict` passed, installed into clean venvs (with and without the `mcp` extra), sdist test suite passes from a clean extraction; `test_mcp_without_the_extra_exits_2_with_the_install_hint`. Not yet: a real upload, `[project.urls]` (no public remote), CI/release workflows have never run |
| `ia.claude_registration` | `claude mcp add` | `[part]` | registered at user scope, `claude mcp list` reports Connected, all nine tools driven over stdio against the real corpus with zero errors. The running session's own tool list was not reloaded, so the model-facing path is unexercised |

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
