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
- **MCP server (needs `itulib[mcp]`).** Ten tools (`itu_search`, `itu_read`, `itu_cite`, `itu_links`,
  `itu_browse`, `itu_outline`, `itu_grep`, `itu_errata`, `itu_compare`, `itu_info`), the `itu://{rec}/{number}` resource
  template, and the `explain_clause` and `verify_claim` prompts. Results are token-budgeted and paged, and say
  whether a list was truncated.
- **References.** One grammar (`X.690§11.6¶2`) accepted by every tool; `¶n` is the nth sentence of the extracted
  clause. Cross-references and back-references between clauses; a `normative` view of shall/should/may
  sentences.
- **Search.** Clauses matching every term come first; partial matches fill the list and are marked.
- **Structure from the document.** Clauses come from each PDF's own bookmarks (contents lines as the fallback):
  exact heading titles, heading-only parents indexed, annexes included; deeper numbered paragraphs are
  accepted only as strict successors. 99.8% of the 1,261 listed headings are located; duplicate clause numbers
  are 0 except X.692 (11). Running page headers and footers are stripped from clause text.
- **Catalogue.** `itulib catalog sync | list | show` and the `itu_catalog` tool read ITU's series listings, recommendation
  pages and component pages (one request per second, cached, `/rec/` only) into a local manifest of editions and the
  formats each is offered in. Metadata only; nothing is downloaded. Checked against the real site: 756 listings in
  series X, and the crawled PDF sizes and ids for X.680, X.690 and X.691 equal the independently measured ones.
- **Editions.** X.690 (11/2008) and (08/2015) are fetchable with `itulib sync --all`; `itulib compare` and `itu_compare` show what changed in a clause by sentence.
- **Ranking.** Real headings are indexed in their own column and weighted above body text; filler words are
  dropped from queries; partial matches top up a short result list and are marked `some terms`. The index
  carries a schema version and an older one is refused with the command to rebuild it.
- **Segmentation fixes.** Pointers such as "see 8.1.2", DOI fragments, history-table rows and `x.0` numbers no
  longer become clauses (X.690: 22 duplicate clause numbers down to 3); lettered annex clauses (A.1, C.3.2) are
  indexed; titles are not cut at "Rec.".
- **Known limits** are listed in the README. Ambiguous clause numbers are flagged with a `warning`.
