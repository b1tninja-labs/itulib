"""Segmentation quality over the fetched corpus: how much of each document's own heading list is located.

Not part of the test suite (it needs the corpus, which tests/test_license.py forbids tests to require) and not
shipped in the sdist. Run it after changing `text.py` or after registering a new recommendation:

    python scripts/measure_segmentation.py              # every fetched in-force edition
    python scripts/measure_segmentation.py X.509 X.501  # only these

For each edition it prints the number of bookmarks that parse as numbered headings (`listed`), how many of
those the splitter located in the extracted text (`found`), the clause count, duplicate clause numbers, and
the headings that have no text of their own. `listed` is 0 when the PDF has no usable bookmarks and the
contents-page fallback is the only source. No specification text is printed or kept.
"""

from __future__ import annotations

import sys
from collections import Counter

from itulib import corpus, sources, text


def measure(edition: sources.Edition) -> str:
    pdf = corpus.require(edition)
    extracted = text.pages(pdf)
    listed = text.headings(pdf, extracted)
    rows = text.clauses(extracted, listed)
    flat = text.tidy("\n".join(line for line in "\n".join(extracted).splitlines() if not text.LEADER.search(line)))
    found = len(text._locate(flat, listed))
    duplicates = sum(count - 1 for count in Counter(row.number for row in rows).values() if count > 1)
    heading_only = sum(1 for row in rows if row.heading and not row.body.strip())
    recall = f"{100 * found / len(listed):.1f}%" if listed else "n/a"
    return (
        f"{edition.key:16} listed {len(listed):5}  found {found:5}  recall {recall:>6}  "
        f"clauses {len(rows):5}  duplicates {duplicates:3}  heading-only {heading_only:4}"
    )


def main(argv: list[str]) -> int:
    targets = [sources.resolve(name) for name in argv] or list(sources.IN_FORCE)
    for edition in targets:
        if not corpus.has(edition):
            print(f"{edition.key:16} not fetched: run `itulib fetch {edition.key}`")
            continue
        print(measure(edition))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
