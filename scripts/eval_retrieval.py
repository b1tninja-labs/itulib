"""Retrieval quality over the fetched corpus: does the question land on the clause that answers it?

Not part of the test suite (it needs the corpus, which tests/test_license.py forbids tests to require) and not
shipped in the sdist. Run it after changing search, ranking or segmentation:

    python scripts/eval_retrieval.py            # summary and misses
    python scripts/eval_retrieval.py --verbose  # every query with its top hits

Each case is a question and the clause numbers that answer it. A result is correct when it IS one of those
clauses or lies inside one (8.1.2.4.2 is inside 8.1.2.4). The expectations were set by reading the titles of
the clauses the search returned for the first version of these questions, not from memory of the standard, and
they hold only clause numbers: no specification text is kept here.

Metrics: hit@1, hit@5 and mean reciprocal rank over the top 5.
"""

from __future__ import annotations

import argparse
import sys

from itulib import corpus, index, sources

CASES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("X.690", "high tag number identifier octets", ("8.1.2.4",)),
    ("X.690", "indefinite length form of length octets", ("8.1.3",)),
    ("X.690", "definite length form", ("8.1.3",)),
    ("X.690", "integer encoding minimum number of octets", ("8.3",)),
    ("X.690", "boolean true value encoding", ("8.2", "11.1")),
    ("X.690", "set-of encodings ordered", ("11.6",)),
    ("X.690", "object identifier first two arcs encoded", ("8.19",)),
    ("X.690", "generalized time encoding", ("11.7", "8.25")),
    ("X.690", "UTCTime encoding seconds", ("11.8",)),
    ("X.690", "real value base encoding", ("8.5", "11.3")),
    ("X.690", "null value encoding", ("8.8",)),
    ("X.690", "bitstring unused bits", ("11.2", "8.6")),
    ("X.690", "end-of-contents octets", ("8.1.5", "3.7")),
    ("X.690", "set components canonical order tag", ("9.3", "10.3")),
    ("X.690", "encoding of an enumerated value", ("8.4",)),
    ("X.690", "restrictions on BER used by both CER and DER", ("11",)),
    ("X.690", "distinguished encoding rules", ("10",)),
    ("X.690", "encoding for a value of a CHOICE type", ("8.13",)),
)


def correct(number: str, wanted: tuple[str, ...]) -> bool:
    return any(number == w or number.startswith(w + ".") for w in wanted)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--k", type=int, default=5)
    args = parser.parse_args()
    top1 = topk = 0
    reciprocal = 0.0
    misses: list[str] = []
    for rec, query, wanted in CASES:
        edition = sources.resolve(rec)
        if not corpus.has(edition):
            print(f"{rec} is not fetched: run `itulib sync`", file=sys.stderr)
            return 3
        hits, relaxed = index.search_mode(edition, query, args.k)
        rank = next((i for i, h in enumerate(hits, start=1) if correct(h.number, wanted)), 0)
        top1 += rank == 1
        topk += rank > 0
        reciprocal += 1 / rank if rank else 0.0
        if not rank:
            misses.append(f"{rec} {query!r} wanted {wanted}, got {[h.number for h in hits]}")
        if args.verbose:
            shown = ", ".join(f"{h.number}{'*' if correct(h.number, wanted) else ''}" for h in hits)
            print(f"{'ok  ' if rank else 'MISS'} {query!r}{' [relaxed]' if relaxed else ''}: {shown}")
    n = len(CASES)
    summary = f"hit@1 {top1}/{n} ({100 * top1 / n:.0f}%)  hit@{args.k} {topk}/{n} ({100 * topk / n:.0f}%)"
    print(f"cases {n}  {summary}  MRR {reciprocal / n:.3f}")
    for line in misses:
        print("  miss:", line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
