# Changelog

## 0.1.0 (unreleased)

First release intended for PyPI.

- **Corpus.** The twelve ASN.1 recommendations X.680-X.683 and X.690-X.697 (02/2021), plus X.690 Erratum 1
  (09/2021), registered with SHA-256 digests measured from the downloaded files. `itulib fetch` verifies a
  digest and refuses a mismatch; `itulib sync` fetches and indexes everything and exits non-zero if any item
  failed. The ITU-T series index (A-Z) is browsable.
- **Nothing from ITU is shipped.** The text is fetched into `$ITULIB_HOME` (default `~/.itulib`). A test fails if
  a PDF or a verbatim clause sentence appears anywhere in the tree.
- **CLI.** `info`, `fetch`, `sync`, `index`, `search`, `read`, `cite`, `links`, `grep`, `browse`, `errata`,
  `mcp`.
- **MCP server (needs `itulib[mcp]`).** Nine tools (`itu_search`, `itu_read`, `itu_cite`, `itu_links`,
  `itu_browse`, `itu_outline`, `itu_grep`, `itu_errata`, `itu_info`), the `itu://{rec}/{number}` resource
  template, and the `explain_clause` and `verify_claim` prompts. Results are token-budgeted and paged, and say
  whether a list was truncated.
- **References.** One grammar (`X.690§11.6¶2`) accepted by every tool; `¶n` is the nth sentence of the extracted
  clause. Cross-references and back-references between clauses; a `normative` view of shall/should/may
  sentences.
- **Search.** Every term must match; if nothing does, terms are OR-ed and the result is marked `relaxed`.
- **Segmentation fixes.** Pointers such as "see 8.1.2", DOI fragments, history-table rows and `x.0` numbers no
  longer become clauses (X.690: 22 duplicate clause numbers down to 3); lettered annex clauses (A.1, C.3.2) are
  indexed; titles are not cut at "Rec.".
- **Known limits** are listed in the README. Ambiguous clause numbers are flagged with a `warning`.
