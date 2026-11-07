"""PDF to clauses. The unit of citation in an ITU recommendation is the subclause, not the page.

Extraction is lossy in ways that matter to a citation: ITU's PDFs emit "Rec. ITU -T X.680" with a stray space,
hyphenate "set -of" and "ISO/IEC 8824 -1". `tidy` repairs the three artefacts actually observed in 02/2021, and the
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
from pypdf.errors import PdfReadError

# Numeric (8.1.2.4) or annex (A.1, C.3.2) numbering. Annex letters stop at I: past that they collide with
# recommendation names ("G.711", "H.323") far more often than they head a clause.
CLAUSE_NUMBER = re.compile(r"(?<![\w.])((?:\d{1,2}|[A-I])(?:\.\d{1,2}){1,5})\s")
# A row of the document-history table ("1.1 ITU-T X.690 (1994) Cor. 1 ...") looks like clause 1.1.
HISTORY_ROW = re.compile(r"ITU-T\s+[A-Z]\.\d+\s*\(?\d{4}")
# "ISO/IEC 8824 -1": the extractor puts a space before the part number of a joint designation.
ISO_PART = re.compile(r"(\d{4}) -(\d)")
LEADER = re.compile(r"\.{5,}")
SPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class Clause:
    number: str
    title: str
    body: str
    heading: bool = False  # title is the document's own heading, not the first sentence

    def cite(self, edition_key: str) -> str:
        return f"Rec. ITU-T {edition_key} §{self.number}"


def tidy(text: str) -> str:
    """Repair the three extraction artefacts observed in 02/2021. Lossy, and said so on purpose."""
    text = text.replace("ITU -T", "ITU-T").replace("set -of", "set-of")
    return SPACE.sub(" ", ISO_PART.sub(r"\1-\2", text)).strip()


def pages(path: object) -> list[str]:
    reader = PdfReader(str(path))
    return strip_running_lines([page.extract_text() or "" for page in reader.pages])


def strip_running_lines(page_texts: list[str]) -> list[str]:
    """Drop running page headers and footers ("ISO/IEC 8825-1:2021 (E) 14", "Rec. ITU-T X.690 (02/2021)").

    They land in the middle of a clause when a clause crosses a page, which corrupts quoting and makes the same
    sentence differ between editions. A line is running text when, with its digits masked, it contains a digit
    (a page or edition number) and repeats on at least a quarter of the pages. Requiring the digit keeps a
    legitimately repeated word such as a table caption.
    """
    if len(page_texts) < 4:
        return page_texts

    def masked(line: str) -> str:
        return re.sub(r"\d+", "#", line.strip())

    seen: dict[str, int] = {}
    for page in page_texts:
        for key in {masked(line) for line in page.splitlines() if line.strip()}:
            seen[key] = seen.get(key, 0) + 1
    threshold = max(3, len(page_texts) // 4)
    # A clause heading masks to the same string every time it repeats ("10.1 General", "18.1 General" ->
    # "#.# General"), so lines that start with a clause number are never running text.
    numbered = re.compile(r"^(?:#|[A-I])(?:\.#)+\s")
    running = {
        key
        for key, count in seen.items()
        if count >= threshold and "#" in key and len(key) <= 90 and not numbered.match(key)
    }
    return ["\n".join(line for line in page.splitlines() if masked(line) not in running) for page in page_texts]


_TITLE_END = re.compile(r"(?<!Rec)(?<!e\.g)(?<!i\.e)(?<!Fig)(?<!No)(?<!cf)(?<!Cor)(?<!Amd)\. ")


def _heading(chunk: str) -> str:
    """First sentence of the chunk, capped. A heading and its first rule are not separable in extracted
    text — `11.6 Set-of components The encodings of…` runs straight on — so the title is offered as a label
    and `body` stays authoritative."""
    cut = _TITLE_END.search(chunk)
    head = chunk if cut is None else chunk[: cut.start()]
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


def _plausible_heading(flat: str, start: int, number: str) -> bool:
    """Annex numbers (A.1) are only headings at a sentence boundary: elsewhere they are far more likely to be
    a reference ("Part 2, D.2)"), a recommendation name, or an enumerator."""
    if number[0].isdigit():
        return True
    before = flat[:start].rstrip()
    return not before or before[-1] in ".:;)"


_HEADING_TITLE = re.compile(r"^((?:\d{1,2}|[A-I])(?:\.\d{1,2})*)\s+(\S.*)$")
_ANNEX_TITLE = re.compile(r"^Annex\s+([A-I])\b\s*[-\u2013\u2014:.]*\s*(.*)$")
_TOC_LINE = re.compile(r"^\s*((?:\d{1,2}|[A-I])(?:\.\d{1,2})*)\s+(.*?)[\s.]*\.{3,}[\s.\d]*$")


def headings(path: object, page_text: list[str] | None = None) -> list[tuple[str, str]]:
    """The recommendation's own list of numbered headings, in document order: (number, title).

    The PDF bookmarks are the source: ITU's PDFs carry one per heading down to three or four levels, with the
    exact title. The contents pages are the fallback when a PDF has none. Deeper numbered paragraphs
    (8.1.2.4.2) are in neither, and are found by `clauses` from their position instead.
    """
    found: list[tuple[str, str]] = []

    def walk(items: list[object]) -> None:
        for item in items:
            if isinstance(item, list):
                walk(item)
                continue
            title = SPACE.sub(" ", str(getattr(item, "title", ""))).strip()
            match = _HEADING_TITLE.match(title)
            annex = _ANNEX_TITLE.match(title)
            if match:
                found.append((match.group(1), tidy(match.group(2))))
            elif annex:
                found.append((annex.group(1), tidy(annex.group(2)) or f"Annex {annex.group(1)}"))

    try:
        walk(list(PdfReader(str(path)).outline))
    except (PdfReadError, ValueError, OSError):
        found.clear()  # not a readable PDF: fall through to the contents lines
    if found:
        return found
    for line in "\n".join(page_text if page_text is not None else pages(path)).splitlines():
        toc = _TOC_LINE.match(line)
        if toc:
            found.append((toc.group(1), tidy(toc.group(2))))
    return found


def _key(number: str) -> tuple[int | str, ...]:
    return tuple(int(part) if part.isdigit() else part for part in number.split("."))


def _is_successor(last: tuple[int | str, ...], candidate: tuple[int | str, ...]) -> bool:
    """Whether `candidate` can directly follow `last` in a numbered document: its first child (8.1 -> 8.1.1), its
    next sibling (8.1.2 -> 8.1.3), or the next sibling of an ancestor (8.1.2.4 -> 8.1.3). Anything else in the
    middle of a clause is a pointer, an enumerator or a stray number, which is exactly what the unconstrained
    splitter was mistaking for headings."""
    if candidate[:-1] == last and candidate[-1] == 1:
        return True
    for depth in range(1, len(last) + 1):
        parent, tail = last[: depth - 1], last[depth - 1]
        if isinstance(tail, int) and candidate == (*parent, tail + 1):
            return True
    return False


def _title_pattern(title: str) -> re.Pattern[str] | None:
    words = tidy(title).split()
    if not words:
        return None
    return re.compile(r"\s*".join(re.escape(word) for word in words), re.IGNORECASE)


def _locate(flat: str, listed: list[tuple[str, str]]) -> list[tuple[str, str, int, int]]:
    """Find each listed heading in the text, in order: (number, title, start, end-of-title).

    The number alone is not enough (every pointer to "8.1" matches it), so the title has to follow, and the search
    only moves forward, so a heading cannot be satisfied by an earlier cross-reference.
    """
    out: list[tuple[str, str, int, int]] = []
    cursor = 0
    for number, title in listed:
        pattern = _title_pattern(title)
        # A top-level annex is bookmarked as "A" but printed as "Annex A".
        label = r"Annex\s+" + number + r"[\s\-–—:.]*" if number.isalpha() else re.escape(number) + r"\s+"
        head = re.compile(r"(?<![\w.])" + label)
        for match in head.finditer(flat, cursor):
            if _is_reference(flat, match.start()):
                continue
            tail = pattern.match(flat, match.end()) if pattern else None
            if tail is None and pattern is not None:
                short = _title_pattern(" ".join(title.split()[:4]))
                tail = short.match(flat, match.end()) if short else None
            if tail is not None:
                out.append((number, title, match.start(), tail.end()))
                cursor = tail.end()
                break
    return out


def _body_after_title(flat: str, start: int, stop: int) -> str:
    return flat[start:stop].strip()


def clauses(source: list[str] | str, listed: list[tuple[str, str]] | None = None) -> tuple[Clause, ...]:
    """Split recommendation text into clauses.

    With `listed` (the recommendation's own headings, from `headings`) the structure comes from the document:
    every listed heading found in order becomes a clause with its exact title, headings with no text of their
    own included, and numbered paragraphs inside it are accepted only as strict successors. Without it, the
    older heuristic applies: any dotted number that is not a pointer.
    """
    raw = source if isinstance(source, str) else "\n".join(source)
    # Contents lines are dropped whole. Stripping the dot leaders instead leaves "11.2 Unused bits 20" behind,
    # which is a heading-shaped fragment that runs on into the next section and gets indexed as if it were
    # the rule itself.
    kept = [line for line in raw.splitlines() if not LEADER.search(line)]
    flat = tidy("\n".join(kept))
    if listed:
        return _clauses_from_headings(flat, listed)
    marks = [
        (match.group(1), match.start(), match.end())
        for match in CLAUSE_NUMBER.finditer(flat)
        if not match.group(1).endswith(".0")
        and not _is_reference(flat, match.start())
        and _plausible_heading(flat, match.start(), match.group(1))
    ]
    found: list[Clause] = []
    for index, (number, _start, end) in enumerate(marks):
        stop = marks[index + 1][1] if index + 1 < len(marks) else len(flat)
        body = flat[end:stop].strip()
        if len(body) < 20 or HISTORY_ROW.match(body):
            continue
        found.append(Clause(number=number, title=_heading(body), body=body))
    return tuple(found)


def _clauses_from_headings(flat: str, listed: list[tuple[str, str]]) -> tuple[Clause, ...]:
    located = _locate(flat, listed)
    found: list[Clause] = []
    for index, (number, title, _start, title_end) in enumerate(located):
        region_end = located[index + 1][2] if index + 1 < len(located) else len(flat)
        # Numbered paragraphs inside this heading's region, accepted only as successors of the previous one.
        marks: list[tuple[str, int, int]] = []
        last = _key(number)
        for match in CLAUSE_NUMBER.finditer(flat, title_end, region_end):
            candidate = match.group(1)
            if (
                _is_successor(last, _key(candidate))
                and not candidate.endswith(".0")
                and not _is_reference(flat, match.start())
            ):
                marks.append((candidate, match.start(), match.end()))
                last = _key(candidate)
        first_stop = marks[0][1] if marks else region_end
        found.append(
            Clause(number=number, title=title, body=_body_after_title(flat, title_end, first_stop), heading=True)
        )
        for position, (candidate, _s, end) in enumerate(marks):
            stop = marks[position + 1][1] if position + 1 < len(marks) else region_end
            body = flat[end:stop].strip()
            if len(body) >= 20 and not HISTORY_ROW.match(body):
                found.append(Clause(number=candidate, title=_heading(body), body=body))
    return tuple(found)


def find(clauses_in: tuple[Clause, ...], number: str) -> Clause | None:
    return next((clause for clause in clauses_in if clause.number == number), None)


_STOPWORDS = frozenset(
    [
        "a",
        "an",
        "the",
        "of",
        "for",
        "in",
        "on",
        "to",
        "and",
        "or",
        "is",
        "are",
        "be",
        "by",
        "with",
        "as",
        "at",
        "from",
        "that",
        "this",
        "it",
        "its",
        "into",
        "than",
    ]
)


def fts_query(raw: str, *, any_term: bool = False) -> str:
    """Turn a user query into something FTS5 will accept.

    A raw query is not a valid MATCH expression: `set-of value order` parses as `set` NEAR `-of` (an
    unsupported-unary-not) and raised OperationalError out of a search tool, which is exactly the wrong shape
    of failure - the caller sees a crash where it should see either an answer or a stated error. Each token is
    quoted, and internal double quotes are doubled, which is FTS5's own escape. The cost is that advanced
    syntax (`AND`, `NEAR`, prefix `*`) stops working from the query box; that is the honest trade, and it is
    said here rather than left for a user to discover.
    """
    tokens = [token for token in raw.split() if token]
    # Filler words must not be required terms ("encoding for a value of a CHOICE type" matches no clause that
    # contains every one of those words), but a query made only of them is still a query.
    content = [token for token in tokens if token.lower() not in _STOPWORDS]
    tokens = content or tokens
    if not tokens:
        raise ValueError("empty query: there is nothing to search for")
    joiner = " OR " if any_term else " "
    return joiner.join(f'"{token.replace(chr(34), chr(34) * 2)}"' for token in tokens)


# --- segmenting, normative statements and references -------------------------------------------------------

_ABBREVIATIONS = ("Rec.", "e.g.", "i.e.", "No.", "Fig.", "Figs.", "Tab.", "etc.", "cf.", "vs.", "ITU-T.")
_SENTENCE_BREAK = re.compile(r"(?<=[.;:])\s+(?=[A-Z(])")
_NORMATIVE = re.compile(r"\b(shall(?: not)?|should(?: not)?|must(?: not)?|may)\b")
_N = r"(?:\d{1,2}|[A-I])(?:\.\d{1,2})+"
_INTERNAL = re.compile(rf"(?:clauses?|sub-?clauses?|§)\s*({_N}(?:\s*(?:,|and|or|to)\s*{_N})*)")
_NUMBER_AT = re.compile(rf"(?<![\w.])({_N})(?![\d.]*\d)")
_NUMBER = re.compile(_N)
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
    bare: tuple[str, ...]  # dotted numbers after "see"/"in"/"of"...: pointers if, and only if, the clause exists
    recommendations: tuple[str, ...]
    standards: tuple[str, ...]


def refs(body: str) -> Refs:
    """What a clause points at: other clauses of the same document, other recommendations, ISO/IEC and RFCs.

    Only references introduced by a word such as "clause" or the section sign count as clause references;
    a bare dotted number is more often a version, an arc or an octet range than a pointer. Numbers after a
    weaker introducer ("see 8.1.3", "as in 8.1.3.2") are returned separately as `bare`: callers should keep
    one only if that clause exists, because nothing else distinguishes it from an arc or a version.
    """
    seen: dict[str, None] = {}
    for match in _INTERNAL.finditer(body):
        for number in _NUMBER.findall(match.group(1)):
            seen.setdefault(number)
    bare = dict.fromkeys(
        m.group(1) for m in _NUMBER_AT.finditer(body) if m.group(1) not in seen and _is_reference(body, m.start())
    )
    recs = dict.fromkeys(m.group(1) for m in _REC.finditer(body))
    standards = dict.fromkeys([m.group(0) for m in _ISO.finditer(body)] + [m.group(0) for m in _RFC.finditer(body)])
    return Refs(tuple(seen), tuple(bare), tuple(recs), tuple(standards))


def parse_ref(raw: str) -> tuple[str | None, str, int | None]:
    """`X.690§11.6¶2`, `X.690 11.6`, `§11.6`, `11.6¶2` -> (rec or None, clause number, ¶ or None)."""
    match = re.fullmatch(
        r"\s*(?:([A-Z]\.\d+(?:#[\d-]+)?)\s*)?§?\s*((?:\d{1,2}|[A-I])(?:\.\d+)*)(?:\s*¶\s*(\d+))?\s*", raw
    )
    if not match:
        raise ValueError(f"{raw!r} is not a clause reference; expected e.g. X.690§11.6 or 11.6¶2")
    return match.group(1), match.group(2), int(match.group(3)) if match.group(3) else None
