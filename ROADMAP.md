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
| `ia.sources_registry` | PLAN.md §1 | `[ok]` | `tests/test_sources.py::test_in_force_editions_are_pinned_and_sized`, `tests/test_sources.py::test_resolve_refuses_to_guess` — digests and sizes pinned from bytes measured 2026-11-07 |
| `ia.fetch_verify` | ITU `dologin_pub.asp` PDF path | `[part]` | `itulib/corpus.py` — verified live (840,764 B and 2,088,934 B, digests matched, into `~/.itulib`). Cannot be a CI test: it is a network fetch of licensed text, so the digest check goes unexercised after the session that ran it |
| `ia.clause_split` | numbered subclause headings | `[ok]` | `tests/test_text.py::test_real_clauses_are_found_with_their_numbers`, `tests/test_text.py::test_dot_leaders_are_dropped_rather_than_indexed`, `tests/test_text.py::test_bodyless_headings_are_not_indexed` |
| `ia.fts_query` | FTS5 MATCH syntax | `[ok]` | `tests/test_text.py::test_hyphenated_queries_survive_the_search_sanitiser` — found live: `set-of value order` raised `OperationalError` and crashed the MCP tool, because FTS5 reads a hyphen as NOT |
| `ia.index_digest_staleness` | index carries the PDF sha256 | `[ok]` | `tests/test_index_and_mcp.py::test_index_refuses_to_serve_after_the_corpus_changes`, `tests/test_index_and_mcp.py::test_a_missing_index_is_an_error_not_an_empty_result`, `tests/test_index_and_mcp.py::test_an_extractor_that_finds_nothing_refuses_to_write_an_index` — over invented text and a stand-in file, since the index only hashes the bytes |
| `ia.mcp_stdio` | MCP over stdio | `[ok]` | `tests/test_index_and_mcp.py::test_mcp_stdio_handshake_lists_ten_tools_and_reports_a_missing_corpus` drives the real server over stdio (the stdout-notice bug fails it at the handshake) and checks that a missing corpus is an error object. Clause answers from the real PDF are still verified by hand only |
| `ia.missing_corpus_not_empty` | error, not empty result | `[ok]` | registry errors return an object naming the remedy (`tests/test_sources.py::test_resolve_refuses_to_guess`); same shape for a corpus never fetched. The bug guarded against is `sync_roadmap.graphql()` swallowing a scope failure into `""` |
| `ia.erratum_artefact_ids` | X.690 (2021) Erratum 1 (09/21) | `[part]` | id found on the erratum's own page (`T-REC-X.690-202109-I!Err1!PDF-E`, not the guessed `!!ERSN1-E`); fetched live, 194,138 B matching ITU's listing, digest pinned. `tests/test_sources.py::test_every_amendment_with_a_download_id_is_pinned`, `tests/test_sources.py::test_resolve_document_finds_an_erratum_and_still_refuses_to_guess`. Gaps: the fetch itself is unexercised in CI, and the note is a one-page covering note that replaces Figure 4 (high-tag-number identifier octets) with a picture, so the extract names the correction but cannot show the corrected octets; the PDF is the authority. Amendment 2 (06/06) still has no id |
| `ia.catalog_asn1` | X.680-X.697 in force | `[part]` | twelve editions registered with digests measured 2026-11-07 (`tests/test_sources.py` pins shape and uniqueness); `itulib sync` fetched and indexed all twelve live. The fetch is unexercised in CI. Joint ISO/IEC designations deliberately not recorded: not verified |
| `ia.series_index` | ITU-T series A-Z | `[part]` | `sources.SERIES` and `itu_browse`; titles copied from ITU's index page, L truncated there and left truncated. Only the ASN.1 recommendations are registered; no other family is |
| `ia.paging` | rfclib `read` paging | `[ok]` | `tests/test_navigation.py::test_paging_follows_next_and_loses_nothing`, `tests/test_navigation.py::test_a_page_always_makes_progress_even_if_one_sentence_exceeds_the_budget`. Unit is the **sentence**, not ITU paragraphing: extraction flattens it, so `¶n` is the nth sentence of the extracted clause |
| `ia.budgets` | token-bounded search/grep | `[part]` | `tests/test_navigation.py::test_grep_is_budgeted_and_says_when_it_stopped` pins the grep half. Gap: `itu_search` budgets the same way but has no direct test, so a regression in the search budget fails nothing |
| `ia.refs_links_cite` | rfclib `links`/`cite`/refs | `[part]` | `tests/test_navigation.py::test_refs_need_an_introducing_word_so_versions_and_arcs_do_not_count`, `tests/test_navigation.py::test_links_resolve_and_report_back_references`, `tests/test_navigation.py::test_citation_comes_from_the_registry`. Recall unmeasured: only references introduced by "clause", "subclause" or the section sign are followed |
| `ia.normative_view` | rfclib `view=normative` | `[part]` | `tests/test_navigation.py::test_normative_picks_obligation_sentences_only`; counts "may", so permissions appear beside obligations |
| `ia.clause_splitter_fidelity` | clauses from the document's own structure | `[part]` | bookmark-guided: `tests/test_navigation.py::test_listed_headings_give_exact_titles_and_keep_heading_only_parents`, `tests/test_navigation.py::test_numbered_paragraphs_are_accepted_only_as_successors`, `tests/test_navigation.py::test_a_pointer_that_matches_a_listed_number_is_not_its_heading`, `tests/test_navigation.py::test_headings_fall_back_to_contents_lines_when_there_are_no_bookmarks`. Measured on the real PDFs (not CI): 99.8% of 1,261 listed headings located, 0 duplicate numbers except X.692 (11). The numbered paragraphs below the bookmarks are inferred from sequence and unmeasured; figures and tables are lost |
| `ia.running_lines` | page headers/footers out of clause text | `[ok]` | `tests/test_text.py::test_running_headers_and_footers_are_stripped_but_repeated_words_are_not`, `tests/test_text.py::test_repeated_numbered_headings_are_not_running_text` (the second is a regression: X.693 lost 23 headings to the first version of the filter) |
| `ia.superseded_editions` | X.690 2008-11, 2015-08 | `[part]` | registered with digests, fetched and indexed; base texts only (corrigenda not applied). The old `-I` ids returned 'Document Not Found'; superseded editions use `-S` |
| `ia.compare_editions` | `itulib compare` / `itu_compare` | `[part]` | tested only through index-level synthetic text via the sentence matcher in `index.compare`; the real 2008-vs-2021 run reports 23 of 245 shared clauses differing, spot-checked, and ignores symbol-only changes |
| `ia.retrieval_eval` | hit@k / MRR | `[part]` | `scripts/eval_retrieval.py`, 18 cases, hit@1 15/18, hit@5 18/18, MRR 0.900. The expectations were set after seeing early results, so these numbers are optimistic; it is a regression guard, not an unbiased benchmark |
| `ia.heading_only_parents` | read "8.1.2" | `[ok]` | `tests/test_navigation.py::test_heading_only_parents_expose_their_children` |
| `ia.search_relaxed` | any-term fallback | `[ok]` | `tests/test_navigation.py::test_search_tops_up_with_partial_matches_and_marks_them` (this row used to name `test_search_relaxes_to_any_term_and_says_so`, which does not exist; the test that does checks all-terms-first, the any-term fallback and its `relaxed` flag). Ranking of the fallback is bm25 over OR-ed terms: "OBJECT IDENTIFIER first arc" ranks relative-OID clauses above 8.19; unmeasured beyond spot checks |
| `ia.outline_budget` | paged outline/browse | `[ok]` | `tests/test_navigation.py::test_slice_rows_pages_without_loss_and_always_progresses`; X.692 outline 51k tokens -> 2k per page |
| `ia.packaging` | wheel + sdist | `[part]` | built, `twine check --strict` passed, installed into clean venvs (with and without the `mcp` extra), sdist test suite passes from a clean extraction; `test_mcp_without_the_extra_exits_2_with_the_install_hint`. Not yet: a real upload, `[project.urls]` (no public remote), CI/release workflows have never run |
| `ia.claude_registration` | `claude mcp add` | `[part]` | registered at user scope, `claude mcp list` reports Connected, all nine tools driven over stdio against the real corpus with zero errors. The running session's own tool list was not reloaded, so the model-facing path is unexercised |
| `ia.catalog_crawler` | series listing -> recommendation -> component pages | `[part]` | `itulib/catalog.py`; `tests/test_catalog.py` (parsers on invented pages, pacing, cache, robots-allowed paths, resumable sync, `--reparse`, CLI). Verified against the live site for series X (756 listings) and five recommendations in detail, where crawled PDF sizes and ids equal the pinned ones for X.680/X.690/X.691. **Not done:** a full crawl of any series, other series' pages, and any use of the result to register editions automatically. Two parser bugs were found only by comparing with real pages (the access class of TIES-only files; `!Err1!PDF-E` single-bang ids), so a changed ITU layout will be caught by `sync` refusing an empty parse, not by a test |

## 2. Retiring asn1core's markers

`asn1core/VECTORS.md` marked rows `[verify against X.690]` when a rule came from memory, and one remembered
rule (an illegal OID arc) was already wrong. Each row was queried against the fetched 02/2021 text. The work
lives *in asn1core*: a citation attached to the row and a check of the implementation. That work has landed.
asn1core commit `0fc1e5f` (2026-11-06) retired all nine markers, with edition and subclause in each row, and
`asn1core/VECTORS.md` now records them as resolved. The clauses below were re-read with `itulib read` on
2026-11-06 against the 02/2021 editions.

The statuses are still `[ ]`, and that is deliberate rather than stale: whether these rows may move to
`[part]` or `[ok]` on the strength of asn1core's tests is an open owner decision (see "Open questions"
below). Recording where a clause is is not retiring a marker, and moving a status is not this file's call.

| Obligation | Clause found | Status | Where |
|---|---|---|---|
| `ia.retire_setof_unsorted` | X.690 §11.6 with §10.1 | `[ ]` | `asn1core/VECTORS.md`, `asn1core/asn1core/der.py::check_set_of`. **No defect, and the reason is the finding.** §11.6 pads the shorter encoding with zero octets for comparison only; §10.1 forces definite, minimally-encoded lengths, so two distinct DER TLVs can never stand in a prefix relation, padding cannot change any comparison, and byte-wise `sorted()` is correct. The row should cite both, and note that BER indefinite-length children are where padding would matter — and those are not DER |
| `ia.retire_bool_nonzero` | X.690 §8.2.2 against §11.1 | `[ ]` | BER allows any non-zero contents octet for TRUE, §11.1 narrows it to all-ones under CER/DER. Matches `asn1core/asn1core/der.py::check_boolean` as written; retired in asn1core `0fc1e5f` |
| `ia.retire_int_nonmin` | X.690 §8.3.2 | `[ ]` | minimality stated, with a NOTE giving its purpose. Matches `asn1core/asn1core/der.py::check_integer`; retired in asn1core `0fc1e5f` |
| `ia.repoint_time_leap_second` | X.690 §11.7/§11.8 defer the alphabet; X.680 §47.3 | `[ ]` | **the marker was on the wrong document.** X.690 fixes the form and says nothing about a seconds value of 60 (searched, no match). Re-asked of X.680: §47.3 bounds UTCTime seconds at 00 to 59, so `60` is an ill-formed value, not a legal one the host type cannot express. Re-pointed in asn1core `0fc1e5f`; RFC 5280 §4.1.2.5.1 stays with `rfclib` |
| `ia.retire_oid_first_arc` | X.690 §8.19.4 | `[ ]` | the two-arc combination subclause, read with `itulib read X.690 8.19.4`: the first subidentifier packs the first two components as `(X*40) + Y`, and its NOTE bounds the 0 to 39 range to the nodes under X = 0 and X = 1, so a first component of 2 occupies 80 upward and `0x7F` is `2.47`. This is the row a remembered answer got wrong; asn1core `0fc1e5f` cites §8.19.4 |
| `ia.charsets_from_x680` | X.680 §41.4 Table 10 | `[ ]` | the PrintableString alphabet, read with `itulib read X.680 41.4`; asn1core's `printable-charset` row cites it (`0fc1e5f`). The other restricted alphabets have not been asked |
| `ia.set_vs_setof` | §9.3/§10.3 by tag, §11.6 by encoding | `[ ]` | two rules the current prose collapses into "SET OF is sorted". Belongs beside `check_set_of` in asn1core |
| `ia.retire_tag_nonminimal` | X.690 §8.1.2.4.2 c) | `[ ]` | high-tag-number form: the first octet after the initial one may not have its seven value bits all clear, which is exactly a leading `0x80` (paraphrased). Read with `itulib read X.690 8.1.2.4.2`; asn1core's `tag-nonminimal` row cites it (`0fc1e5f`), and `asn1core/tests/test_defect_corpus.py::test_tag_nonminimal_is_accepted_by_ber_and_refused_by_der` is the behaviour |
| `ia.retire_len_nonminimal` | X.690 §10.1 | `[ ]` | under DER every length is definite and as short as it can be (paraphrased). Read with `itulib read X.690 10.1`; asn1core's `len-nonminimal` row cites it (`0fc1e5f`), and `asn1core/tests/test_defect_corpus.py::test_nonminimal_length_accepted_by_ber_refused_by_der` is the behaviour |

## 3. Deliberate non-goals

| Obligation | Spec | Status | Where |
|---|---|---|---|
| `ia.vendor_the_corpus` | ITU rights notice, page iii | `[no]` | no ITU text in the tree, ever. `tests/test_license.py` guards the easy version and states its own limits; the tempting fix for a failing search test is committing the PDF, and history cannot walk that back |
| `ia.a_second_validator` | DER conformance | `[no]` | itulib answers what a clause says; `asn1core` decides what to accept and `VECTORS.md` stays the exit test |
| `ia.rfclib_overlap` | RFC series | `[no]` | RFC questions go to `rfclib`, which owns that corpus and its errata. This exists only for what is not in the RFC series |
| `ia.ocr_scanned_editions` | superseded editions | `[no]` | lineage registered but not extracted; nothing asks a question of a superseded edition, and unverified OCR of licensed text is worse than none |

## 4. Board projection

The portfolio board is GitHub Project V2 **#4** "Protocol SDK portfolio"; the older #2 of the same title is
gone. This directory (`itulibrary`) now has a public remote, <https://github.com/b1tninja/itulib>, pushed on
2026-11-06, and the portfolio decision is that every project with a matrix is synced and gated, this one
included. Read on 2026-11-06, #4 holds one project-level card for itulib, and it is stale: it still says
"local only" and "8 of 26 obligations done". No row of this matrix has an issue (`b1tninja/itulib` has none).
Projecting the rows is the board re-projection step in `sdk-forge/docs/improvement-plan.md` (WP18), which runs
`sync_roadmap.py` for this repository and then `--check`. Until it has run, an issue count of zero means "not
projected", not "nothing open".

## 5. Open questions

- **Section 2 statuses.** asn1core `0fc1e5f` cites the edition and subclause for every marker. Do the section 2
  rows move to `[part]` until itulib itself quotes each clause, or further? This is an owner decision (D22 in
  `sdk-forge/docs/improvement-plan.md`) and is open, so the rows stay `[ ]`.
- **Milestones.** This matrix has no ladder. A proposed one, taken from PLAN.md §5's exit test, is in Appendix A
  of `sdk-forge/docs/improvement-plan.md`; adopting it is the same open decision, so no Milestone column is
  added here.
- **`len-indefinite`.** asn1core retired a ninth marker on X.690 §8.1.3.2 a) (primitive encodings take the
  definite form) that has no row in section 2. The clause was re-read with `itulib read X.690 8.1.3.2` on
  2026-11-06 and says what asn1core cites. Whether it gets a row here is open.
