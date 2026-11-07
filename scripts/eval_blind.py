"""Blind retrieval benchmark: questions written from the outlines alone, frozen before the first search.

`scripts/eval_retrieval.py` sets its expectations after reading what the search returned, so its numbers
flatter the ranker. This one does not. Protocol, followed in this order:

1. A private ITULIB_HOME was built from the already-fetched PDFs and indexed with `itulib sync`.
2. The cases below were written from `itulib browse <rec> --depth 2|3` listings only: pick a clause by its
   title and position, then phrase the question a developer would ask whose answer is that clause. Some
   questions deliberately avoid the heading's words, a few are hard (the answer sits under a different
   title, or two clauses legitimately answer it).
3. The case list was frozen, and committed on its own, BEFORE `search` was run even once. No case has been
   edited, added or dropped since in the light of a result. Search and ranking code was not tuned for it.

A result is correct when it IS an expected clause or lies inside one (8.1.2.4 is inside 8.1.2). Expectations
hold clause numbers only; no specification text is kept here. Not part of the test suite (it needs the
corpus) and not shipped in the sdist.

    python scripts/eval_blind.py            # per-document and overall hit@1/5/10, MRR, every miss
    python scripts/eval_blind.py --verbose  # every query with its top hits
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict

from itulib import corpus, index, sources

K = 10

# (recommendation, question, expected clauses)
CASES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    # --- X.690 ---
    ("X.690", "How do I encode a BOOLEAN TRUE in DER?", ("11.1", "8.2")),
    ("X.690", "What bytes represent an ASN.1 NULL?", ("8.8",)),
    ("X.690", "How are the first two OID components combined into one subidentifier?", ("8.19",)),
    ("X.690", "How do I encode a relative OID?", ("8.20",)),
    ("X.690", "Must the members of a SET OF be sorted in DER, and by what?", ("11.6",)),
    ("X.690", "In what order should the members of an unordered SET be written in DER?", ("10.3", "9.3")),
    ("X.690", "What must the padding bits of a BIT STRING be set to?", ("11.2",)),
    ("X.690", "Are trailing zero bits removed from named bit lists?", ("11.2",)),
    ("X.690", "How is an INTEGER's two's complement representation limited in leading octets?", ("8.3",)),
    ("X.690", "How do I serialize a floating point number with base 2?", ("8.5", "11.3")),
    ("X.690", "When is the seconds field mandatory in a UTC timestamp string?", ("11.8",)),
    ("X.690", "Should fractional seconds keep trailing zeros in GeneralizedTime?", ("11.7",)),
    ("X.690", "Which time zone designators are allowed for GeneralizedTime in DER?", ("11.7",)),
    ("X.690", "How is a component with a DEFAULT value handled by DER: omitted or included?", ("11.5",)),
    ("X.690", "How does an IMPLICIT tag change the encoding of the underlying type?", ("8.14",)),
    ("X.690", "What marks the end of an indefinite-length encoding?", ("8.1.5",)),
    ("X.690", "How do I encode a tag number greater than 30?", ("8.1.2",)),
    ("X.690", "How is the length encoded when the content is 200 bytes long?", ("8.1.3",)),
    ("X.690", "Can I use constructed strings in DER?", ("10.2",)),
    ("X.690", "How is an ENUMERATED value encoded relative to an INTEGER?", ("8.4",)),
    ("X.690", "Is there a tag for the CHOICE itself, or only for the chosen alternative?", ("8.13",)),
    ("X.690", "How do I encode an open type (the old ANY)?", ("8.15",)),
    ("X.690", "Which object identifiers name the BER, CER and DER transfer syntaxes?", ("12", "B")),
    ("X.690", "How are UTF8String characters turned into octets?", ("8.23",)),
    ("X.690", "Which choices does a BER sender have that CER and DER take away?", ("7.3", "7.4")),
    ("X.690", "Is there a worked example of an encoded record?", ("A",)),
    ("X.690", "How is a DATE value encoded?", ("8.26",)),
    ("X.690", "How do I write a GeneralString in canonical form?", ("11.4",)),
    ("X.690", "Which bit of an octet is the most significant, and how are bits numbered?", ("6",)),
    ("X.690", "How is an empty SEQUENCE OF encoded?", ("8.10",)),
    # --- X.680 ---
    ("X.680", "What is the universal tag number for UTCTime?", ("47",)),
    ("X.680", "How do I define an enumerated type with an extension marker?", ("20",)),
    ("X.680", "Which characters may appear in a PrintableString?", ("41",)),
    ("X.680", "What does AUTOMATIC TAGS in a module header do to components?", ("13.3",)),
    ("X.680", "How do I attach an exception specification to an extension marker?", ("53",)),
    ("X.680", "What is the default tagging mode if a module header says nothing?", ("13.2",)),
    ("X.680", "How do I import a type from another module?", ("13.16",)),
    ("X.680", "How can I refer to one component of a SEQUENCE from elsewhere, with a path?", ("15",)),
    ("X.680", "Which constraint limits the length of a string?", ("51.5",)),
    ("X.680", "How do I restrict a string to a handful of characters?", ("51.7",)),
    ("X.680", "How do I restrict the range of an INTEGER?", ("51.4",)),
    ("X.680", "How do I constrain individual components of a SEQUENCE OF values?", ("51.8",)),
    ("X.680", "What may an identifier start with, and can it contain hyphens?", ("12.3",)),
    ("X.680", "How are comments written in ASN.1?", ("12.6",)),
    ("X.680", "What are the tag numbers of SET and SET OF?", ("27.5", "28.2")),
    ("X.680", "Which tag numbers are assigned to the universal class types?", ("8.4",)),
    ("X.680", "What does it mean for tags to have a canonical order?", ("8.6", "8.5")),
    ("X.680", "Which words are reserved and cannot be used as references?", ("12.38",)),
    ("X.680", "How do I define a type as one alternative selected out of a CHOICE?", ("30",)),
    ("X.680", "How do I specify a type holding a date, a time, or both?", ("38",)),
    ("X.680", "What is an ObjectDescriptor?", ("48",)),
    ("X.680", "What is the syntax of a hexadecimal string literal?", ("12.12",)),
    ("X.680", "How do union and intersection combine subtype constraints?", ("50",)),
    ("X.680", "What does EXTENSIBILITY IMPLIED do in a module header?", ("13.4",)),
    ("X.680", "What rules must later versions of a type obey so old decoders still work?", ("6", "7", "I")),
    ("X.680", "When are two types compatible?", ("C",)),
    ("X.680", "In what order are the characters of an IA5String considered for range subtyping?", ("43",)),
    # --- X.691 ---
    ("X.691", "How is a BOOLEAN encoded in PER?", ("12",)),
    ("X.691", "How do I encode a constrained integer in aligned PER?", ("13", "11.5")),
    ("X.691", "How is a small number used for an extension index encoded?", ("11.6",)),
    ("X.691", "How is the length prefix encoded for values with no upper bound?", ("11.9",)),
    ("X.691", "How are optional components flagged at the start of a SEQUENCE?", ("19",)),
    ("X.691", "How is the index of a CHOICE alternative encoded?", ("23",)),
    ("X.691", "Which constraints does PER ignore when sizing fields?", ("10.3",)),
    ("X.691", "What is the difference between the aligned and unaligned variants?", ("7.7", "9.2", "9.3", "11.1")),
    ("X.691", "How are known-multiplier character strings packed into bits?", ("30",)),
    ("X.691", "How is an open type field encoded in PER?", ("11.2",)),
    ("X.691", "In what order are ENUMERATED values numbered before encoding?", ("14",)),
    ("X.691", "How is the number of components of a SEQUENCE OF encoded?", ("20",)),
    ("X.691", "How are extension additions of a SEQUENCE encoded?", ("19.7", "19.8", "19.9")),
    ("X.691", "How is a BIT STRING of fixed size encoded without a length?", ("16",)),
    ("X.691", "How is an OCTET STRING with a size constraint encoded?", ("17",)),
    ("X.691", "How are REAL values encoded in PER?", ("15",)),
    ("X.691", "How are SET OF members ordered for the canonical variant?", ("22",)),
    ("X.691", "How is an object identifier encoded in PER?", ("24",)),
    ("X.691", "How is a time value encoded when the property settings say it is a date?", ("32",)),
    ("X.691", "Which PER encoding rule variants exist?", ("7",)),
    ("X.691", "How is a value of the EXTERNAL type encoded in PER?", ("29",)),
    ("X.691", "How is a non-negative binary integer produced with the fewest octets?", ("11.3",)),
    ("X.691", "Which PER encodings can be relayed without knowing the type?", ("7.3",)),
    ("X.691", "Which object identifiers name the PER transfer syntaxes?", ("33",)),
    ("X.691", "Is there an example using extension addition groups?", ("A.4",)),
)


def correct(number: str, wanted: tuple[str, ...]) -> bool:
    return any(number == w or number.startswith(w + ".") for w in wanted)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()
    # per document: [n, hit@1, hit@5, hit@10, sum of reciprocal ranks over the top K]
    tally: dict[str, list[float]] = defaultdict(lambda: [0, 0, 0, 0, 0.0])
    misses: list[str] = []
    for rec, query, wanted in CASES:
        edition = sources.resolve(rec)
        if not corpus.has(edition):
            print(f"{rec} is not fetched: run `itulib sync`", file=sys.stderr)
            return 3
        hits, relaxed = index.search_mode(edition, query, K)
        rank = next((i for i, h in enumerate(hits, start=1) if correct(h.number, wanted)), 0)
        row = tally[rec]
        row[0] += 1
        row[1] += rank == 1
        row[2] += 0 < rank <= 5
        row[3] += rank > 0
        row[4] += 1 / rank if rank else 0.0
        if not rank:
            misses.append(f"{rec} {query!r} wanted {wanted}, got {[h.number for h in hits]}")
        if args.verbose:
            shown = ", ".join(f"{h.number}{'*' if correct(h.number, wanted) else ''}" for h in hits)
            print(f"{'ok  ' if rank else 'MISS'} {rec} {query!r}{' [relaxed]' if relaxed else ''}: {shown}")
    total = [0.0] * 5
    for rec in sorted(tally):
        row = tally[rec]
        total = [a + b for a, b in zip(total, row, strict=True)]
        print(_line(rec, row))
    print(_line("all", total))
    for line in misses:
        print("  miss:", line)
    return 0


def _line(label: str, row: list[float]) -> str:
    n = row[0]
    return (
        f"{label:6} cases {int(n):3}  hit@1 {int(row[1])}/{int(n)} ({100 * row[1] / n:.0f}%)  "
        f"hit@5 {int(row[2])}/{int(n)} ({100 * row[2] / n:.0f}%)  "
        f"hit@10 {int(row[3])}/{int(n)} ({100 * row[3] / n:.0f}%)  MRR {row[4] / n:.3f}"
    )


if __name__ == "__main__":
    raise SystemExit(main())
