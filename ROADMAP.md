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
| `ia.series_index` | ITU-T series A-Z | `[part]` | `sources.SERIES` and `itu_browse`; titles copied from ITU's index page, L truncated there and left truncated. Only the ASN.1 recommendations are registered; no other family is |
| `ia.paging` | rfclib `read` paging | `[ok]` | `tests/test_navigation.py::test_paging_follows_next_and_loses_nothing`, `test_a_page_always_makes_progress_even_if_one_sentence_exceeds_the_budget`. Unit is the **sentence**, not ITU paragraphing: extraction flattens it, so `¶n` is the nth sentence of the extracted clause |
| `ia.budgets` | token-bounded search/grep | `[ok]` | `test_grep_is_budgeted_and_says_when_it_stopped`; `itu_search` budgets the same way but has no direct test |
| `ia.refs_links_cite` | rfclib `links`/`cite`/refs | `[part]` | `test_refs_need_an_introducing_word...`, `test_links_resolve_and_report_back_references`, `test_citation_comes_from_the_registry`. Recall unmeasured: only references introduced by "clause", "subclause" or the section sign are followed |
| `ia.normative_view` | rfclib `view=normative` | `[part]` | `test_normative_picks_obligation_sentences_only`; counts "may", so permissions appear beside obligations |
| `ia.clause_splitter_fidelity` | clauses from the document's own structure | `[part]` | bookmark-guided: `test_listed_headings_give_exact_titles_and_keep_heading_only_parents`, `test_numbered_paragraphs_are_accepted_only_as_successors`, `test_a_pointer_that_matches_a_listed_number_is_not_its_heading`, `test_headings_fall_back_to_contents_lines_when_there_are_no_bookmarks`. Measured on the real PDFs (not CI), 02/2021 editions: 1,292 of 1,293 listed headings located (was 1,289; the remaining one is a bookmark that X.692 lists twice), 0 duplicate clause numbers (was 11, all X.692). The regressions are `test_an_acronym_before_a_heading_is_not_the_word_per`, `test_a_heading_right_after_a_title_ending_in_a_pointer_word_is_still_a_heading`, `test_a_number_that_is_a_located_heading_elsewhere_is_not_also_a_paragraph`. Figures and tables are still lost; annexes whose own heading is not bookmarked are not clauses (see `ia.paragraph_inference`) |
| `ia.paragraph_inference` | numbered paragraphs below the bookmarks | `[part]` | accepted as strict successors; measured 2026-11 against four checks that can fail, over all twelve in-force PDFs (numbers before -> after the fixes in this row). **Leave-one-out:** bookmarks of depth 3 and deeper were withheld and inferred; recovered at the exact bookmarked position 292 of 294 -> 295 of 295, recovered at a wrong position 0 -> 0 (the two lost were X.691 B.2.2 and B.2.3, whose parent heading was not located). **Cross-edition:** paragraph numbers present in one X.690 edition and absent from another (headings excluded, since they are bookmarks): 7 -> 0 for 2015-08 vs 2021-02 and for 2008-11 vs 2021-02 (all seven were Annex C). **Unaccepted heading-shaped numbers** (not pointers, after a sentence end): 71 -> 14, all 14 read by eye and all pointers, foreign numbering or tables of productions. **Cross-references:** of 147 `clause N` pointers 18 resolved to nothing (17 of them cross-document); now 125 own-document pointers, 1 unresolved (a non-ITU Directives document), and 23 classed foreign, 7 of which had silently resolved to the wrong local clause (the totals differ by one because paragraphs were added and removed). Paragraphs: 4,428 -> 4,483 (+66 found, 11 spurious removed: 4,428 + 66 - 11 = 4,483). Pinned in CI only through invented text: `test_a_pointer_followed_by_a_function_word_does_not_take_the_place_of_the_paragraph`, `test_definition_entries_with_lowercase_terms_are_still_paragraphs`, `test_annex_paragraphs_are_found_when_the_bookmarks_skip_the_annex_heading`, `test_an_annex_shaped_number_without_the_annex_heading_is_not_a_paragraph`, `test_a_number_glued_to_the_next_word_is_still_a_paragraph`, `test_pointers_qualified_by_another_recommendation_are_foreign`; the real-corpus numbers need the PDFs. **What the measures cannot tell:** leave-one-out only exercises depths the bookmarks cover (deepest bookmarked level is 3 in X.690, 4 in X.691/X.694) and regions the bookmarks make easy; cross-edition shares the algorithm, so a paragraph both editions lose is invisible; the sibling-gap check is empty by construction (accepted numbers are successors) and found 5 -> 0 only across the final index; "resolves" does not mean "resolves to the right text". **Still wrong:** annexes without their own bookmark (X.681 A-E, X.691 C-E) have no heading clause, so "Annex C <title> (This annex ...)" sits at the end of the previous clause's body; an unbookmarked paragraph shorter than 20 characters is dropped and its text lands in the previous paragraph; one missed number would block every later sibling until the next bookmark (no instance in the corpus); a pointer qualified by this document's own designation is not recognised as such |
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
