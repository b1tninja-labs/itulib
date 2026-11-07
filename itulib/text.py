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


def clauses(source: list[str] | str) -> tuple[Clause, ...]:
    """Split recommendation text into clauses. Anything without a numbered heading is dropped."""
    raw = source if isinstance(source, str) else "\n".join(source)
    # Contents lines are dropped whole. Stripping the dot leaders instead leaves "11.2 Unused bits 20" behind,
    # which is a heading-shaped fragment that runs on into the next section and gets indexed as if it were
    # the rule itself.
    kept = [line for line in raw.splitlines() if not LEADER.search(line)]
    flat = tidy("\n".join(kept))
    marks = [(match.group(1), match.start(), match.end()) for match in CLAUSE_NUMBER.finditer(flat)]
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
