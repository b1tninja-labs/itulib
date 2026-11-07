"""PDF to clauses. The unit of citation in an ITU recommendation is the subclause, not the page.

Extraction is lossy in ways that matter to a citation: ITU's PDFs emit "Rec. ITU -T X.680" with a stray space
and hyphenate "set -of". `tidy` repairs the two artefacts actually observed in the 02/2021 edition, and the
repairs are named here rather than hidden, because a quote that has been silently normalised is a quote that
cannot be checked against the paper. Anything else the extractor mangles stays broken and visible.

Clause boundaries are recognised as a numbered heading: `8.1.2.4 For tags with a number greater than or
equal to 31 ...`. Table-of-contents lines carry dot leaders and are discarded rather than indexed, since an
index whose top hit for "BOOLEAN" is a contents entry answers no question.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from pypdf import PdfReader

CLAUSE_NUMBER = re.compile(r"(?<![\d.])(\d{1,2}(?:\.\d+){1,5})\s")
LEADER = re.compile(r"\.{5,}")
SPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class Clause:
    number: str
    title: str
    body: str

    def cite(self, edition_key: str) -> str:
        return f"Rec. ITU-T {edition_key} §{self.number}"


def tidy(text: str) -> str:
    """Repair the two extraction artefacts observed in 02/2021. Lossy, and said so on purpose."""
    return SPACE.sub(" ", text.replace("ITU -T", "ITU-T").replace("set -of", "set-of")).strip()


def pages(path: object) -> list[str]:
    reader = PdfReader(str(path))
    return [page.extract_text() or "" for page in reader.pages]


def _heading(chunk: str) -> str:
    """First sentence of the chunk, capped. A heading and its first rule are not separable in extracted
    text — `11.6 Set-of components The encodings of…` runs straight on — so the title is offered as a label
    and `body` stays authoritative."""
    cut = chunk.find(". ")
    head = chunk if cut < 0 else chunk[:cut]
    return head[:96].rstrip()


_REFERENCE_WORDS = frozenset(
    [
        "clause",
        "clauses",
        "subclause",
        "subclauses",
        "sub-clause",
        "see",
        "in",
        "of",
        "and",
        "or",
        "to",
        "with",
        "by",
        "from",
        "per",
        "under",
        "table",
        "figure",
        "annex",
        "than",
        "also",
        "both",
        "either",
        "between",
        "through",
    ]
)
_PRECEDING_WORD = re.compile(r"([A-Za-z-]+|§|[,(])\s*$")


def _is_reference(flat: str, start: int) -> bool:
    """True when a dotted number is a pointer ("see 8.1.2") rather than the start of a heading.

    A heading follows a sentence end or the previous clause's text; a pointer follows a word that introduces
    one. Treating the pointer as a heading split clauses mid-sentence and produced duplicate numbers, so that
    `read` could return a fragment of a cross-reference instead of the clause. The cost of the opposite error
    (a real heading right after one of these words) is a clause merged into its neighbour, which is visible in
    the outline rather than silently wrong.
    """
    match = _PRECEDING_WORD.search(flat[max(start - 20, 0) : start])
    if not match:
        return False
    word = match.group(1)
    return word in {"§", ",", "("} or word.lower() in _REFERENCE_WORDS


def clauses(source: list[str] | str) -> tuple[Clause, ...]:
    """Split recommendation text into clauses. Anything without a numbered heading is dropped."""
    raw = source if isinstance(source, str) else "\n".join(source)
    # Contents lines are dropped whole. Stripping the dot leaders instead leaves "11.2 Unused bits 20" behind,
    # which is a heading-shaped fragment that runs on into the next section and gets indexed as if it were
    # the rule itself.
    kept = [line for line in raw.splitlines() if not LEADER.search(line)]
    flat = tidy("\n".join(kept))
    marks = [
        (match.group(1), match.start(), match.end())
        for match in CLAUSE_NUMBER.finditer(flat)
        if not _is_reference(flat, match.start())
    ]
    found: list[Clause] = []
    for index, (number, _start, end) in enumerate(marks):
        stop = marks[index + 1][1] if index + 1 < len(marks) else len(flat)
        body = flat[end:stop].strip()
        if len(body) < 20:
            continue
        found.append(Clause(number=number, title=_heading(body), body=body))
    return tuple(found)


def find(clauses_in: tuple[Clause, ...], number: str) -> Clause | None:
    return next((clause for clause in clauses_in if clause.number == number), None)


def fts_query(raw: str) -> str:
    """Turn a user query into something FTS5 will accept.

    A raw query is not a valid MATCH expression: `set-of value order` parses as `set` NEAR `-of` (an
    unsupported-unary-not) and raised OperationalError out of a search tool, which is exactly the wrong shape
    of failure - the caller sees a crash where it should see either an answer or a stated error. Each token is
    quoted, and internal double quotes are doubled, which is FTS5's own escape. The cost is that advanced
    syntax (`AND`, `NEAR`, prefix `*`) stops working from the query box; that is the honest trade, and it is
    said here rather than left for a user to discover.
    """
    tokens = [token for token in raw.split() if token]
    if not tokens:
        raise ValueError("empty query: there is nothing to search for")
    return " ".join(f'"{token.replace(chr(34), chr(34) * 2)}"' for token in tokens)


# --- segmenting, normative statements and references -------------------------------------------------------

_ABBREVIATIONS = ("Rec.", "e.g.", "i.e.", "No.", "Fig.", "Figs.", "Tab.", "etc.", "cf.", "vs.", "ITU-T.")
_SENTENCE_BREAK = re.compile(r"(?<=[.;:])\s+(?=[A-Z(])")
_NORMATIVE = re.compile(r"\b(shall(?: not)?|should(?: not)?|must(?: not)?|may)\b")
_INTERNAL = re.compile(
    r"(?:clauses?|sub-?clauses?|§)\s*(\d{1,2}(?:\.\d+)+(?:\s*(?:,|and|or|to)\s*\d{1,2}(?:\.\d+)+)*)"
)
_NUMBER = re.compile(r"\d{1,2}(?:\.\d+)+")
_REC = re.compile(r"\b(?:ITU-T\s+)?([A-Z]\.\d{1,4})(?:\s*\|\s*ISO/IEC\s+\d+(?:-\d+)?)?")
_ISO = re.compile(r"\bISO/IEC\s+\d+(?:-\d+)?(?::\d{4})?")
_RFC = re.compile(r"\bRFC\s*\d+")


def sentences(body: str) -> tuple[str, ...]:
    """Split a clause body into citable units.

    The extracted text has no paragraph structure left (`tidy` flattens whitespace, and PDF line breaks carry
    no information), so the unit is the sentence and `¶n` means the nth sentence of the extracted clause. That
    numbering is stable for a digest-pinned edition and is NOT ITU's own paragraphing; a citation that uses it
    should also give the clause number and edition, which `cite` does.
    """
    merged: list[str] = []
    for piece in _SENTENCE_BREAK.split(body):
        if merged and merged[-1].endswith(_ABBREVIATIONS):
            merged[-1] = f"{merged[-1]} {piece}"
        else:
            merged.append(piece)
    return tuple(merged)


def normative(body: str) -> tuple[tuple[int, str], ...]:
    """(¶ index, sentence) for every sentence stating an obligation, permission or recommendation."""
    return tuple((n, s) for n, s in enumerate(sentences(body), start=1) if _NORMATIVE.search(s))


@dataclass(frozen=True)
class Refs:
    clauses: tuple[str, ...]
    recommendations: tuple[str, ...]
    standards: tuple[str, ...]


def refs(body: str) -> Refs:
    """What a clause points at: other clauses of the same document, other recommendations, ISO/IEC and RFCs.

    Only references introduced by a word such as "clause" or the section sign count as clause references;
    a bare dotted number is more often a version, an arc or an octet range than a pointer.
    """
    seen: dict[str, None] = {}
    for match in _INTERNAL.finditer(body):
        for number in _NUMBER.findall(match.group(1)):
            seen.setdefault(number)
    recs = dict.fromkeys(m.group(1) for m in _REC.finditer(body))
    standards = dict.fromkeys([m.group(0) for m in _ISO.finditer(body)] + [m.group(0) for m in _RFC.finditer(body)])
    return Refs(tuple(seen), tuple(recs), tuple(standards))


def parse_ref(raw: str) -> tuple[str | None, str, int | None]:
    """`X.690§11.6¶2`, `X.690 11.6`, `§11.6`, `11.6¶2` -> (rec or None, clause number, ¶ or None)."""
    match = re.fullmatch(r"\s*(?:([A-Z]\.\d+(?:#[\d-]+)?)\s*)?§?\s*(\d{1,2}(?:\.\d+)+)(?:\s*¶\s*(\d+))?\s*", raw)
    if not match:
        raise ValueError(f"{raw!r} is not a clause reference; expected e.g. X.690§11.6 or 11.6¶2")
    return match.group(1), match.group(2), int(match.group(3)) if match.group(3) else None
