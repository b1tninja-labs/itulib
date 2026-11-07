"""A full-text index over one edition, tagged with the digest it was built from.

The index records the sha256 of the PDF it came from and refuses to serve results when the corpus no longer
matches. That is the difference between "this clause says X in the edition you hold" and a stale table that
reports the same confident answer after ITU republished something - a gate that silently skips, in the shape
of a search result.
"""

from __future__ import annotations

import hashlib
import pathlib
import sqlite3
from dataclasses import dataclass

from . import corpus, text
from .sources import Amendment, Edition


@dataclass(frozen=True)
class Hit:
    number: str
    title: str
    excerpt: str
    score: float


def _db_path(edition: Edition) -> pathlib.Path:
    return corpus.home() / "index" / f"{edition.key.replace('#', '-')}.sqlite3"


def build(edition: Edition) -> int:
    """(Re)build the index for one edition. Returns the clause count."""
    pdf = corpus.require(edition)
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    rows = text.clauses(text.pages(pdf))
    if not rows:
        raise RuntimeError(
            f"{edition.key}: extracted 0 clauses. The corpus exists but nothing parsed, which is a failure "
            f"of the extractor, not an empty document. Refusing to write an empty index."
        )
    db = _db_path(edition)
    db.parent.mkdir(parents=True, exist_ok=True)
    db.unlink(missing_ok=True)
    connection = sqlite3.connect(db)
    try:
        connection.executescript(
            """
            CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE VIRTUAL TABLE clause USING fts5(number, title, body, tokenize='porter unicode61');
            """
        )
        connection.executemany(
            "INSERT INTO clause (number, title, body) VALUES (?, ?, ?)",
            [(row.number, row.title, row.body) for row in rows],
        )
        connection.executemany(
            "INSERT INTO meta (key, value) VALUES (?, ?)",
            [("edition", edition.key), ("pdf_sha256", digest), ("clauses", str(len(rows)))],
        )
        connection.commit()
    finally:
        connection.close()
    return len(rows)


def _open(edition: Edition) -> sqlite3.Connection:
    db = _db_path(edition)
    if not db.is_file():
        raise corpus.CorpusMissing(
            f"{edition.key}: no index. Run: python -m itulib.cli fetch {edition.key} && "
            f"python -m itulib.cli index {edition.key}"
        )
    connection = sqlite3.connect(db)
    meta = dict(connection.execute("SELECT key, value FROM meta"))
    pdf = corpus.require(edition)
    if meta.get("pdf_sha256") != hashlib.sha256(pdf.read_bytes()).hexdigest():
        connection.close()
        raise RuntimeError(
            f"{edition.key}: the corpus changed since the index was built. "
            f"Run: python -m itulib.cli index {edition.key}"
        )
    return connection


def search(edition: Edition, query: str, limit: int = 8) -> tuple[Hit, ...]:
    connection = _open(edition)
    try:
        prepared = text.fts_query(query)
    except ValueError:
        connection.close()
        raise
    try:
        cursor = connection.execute(
            "SELECT number, title, snippet(clause, 2, '', '', ' … ', 24), bm25(clause) FROM clause "
            "WHERE clause MATCH ? ORDER BY bm25(clause) LIMIT ?",
            (prepared, limit),
        )
        return tuple(Hit(number=row[0], title=row[1], excerpt=row[2], score=row[3]) for row in cursor)
    finally:
        connection.close()


def read(edition: Edition, number: str) -> text.Clause | None:
    connection = _open(edition)
    try:
        row = connection.execute("SELECT number, title, body FROM clause WHERE number = ?", (number,)).fetchone()
    finally:
        connection.close()
    return text.Clause(number=row[0], title=row[1], body=row[2]) if row else None


def outline(edition: Edition) -> tuple[tuple[str, str], ...]:
    connection = _open(edition)
    try:
        return tuple(
            (row[0], row[1]) for row in connection.execute("SELECT number, title FROM clause ORDER BY rowid")
        )
    finally:
        connection.close()


# --- paging, citation, references ----------------------------------------------------------------------------

CHARS_PER_TOKEN = 4


@dataclass(frozen=True)
class Page:
    """A budgeted slice of one clause. `next` is the ¶ to pass as `start` for the rest, or None at the end."""

    number: str
    title: str
    first: int
    last: int
    total: int
    text: str
    next: int | None


def citation(edition: Edition | Amendment, number: str, para: int | None = None) -> str:
    """`Rec. ITU-T X.690 (02/2021) §11.6¶2`. Built from the registry, never typed by hand."""
    label = edition.edition if isinstance(edition, Edition) else edition.label
    tail = f"¶{para}" if para else ""
    return f"Rec. ITU-T {edition.rec} ({label}) §{number}{tail}"


def page(edition: Edition, number: str, *, start: int = 1, max_tokens: int = 2000) -> Page | None:
    """Sentences `start`.. of a clause, cut at a sentence boundary within the token budget.

    At least one sentence is always returned, so a single over-long sentence cannot stall a caller that is
    following `next`. Each sentence is prefixed with its `[¶n]` so any of them is citable.
    """
    clause = read(edition, number)
    if clause is None:
        return None
    units = text.sentences(clause.body)
    if not 1 <= start <= max(len(units), 1):
        raise ValueError(f"§{number} has {len(units)} sentences; start={start} is outside 1..{len(units)}")
    budget = max(max_tokens, 1) * CHARS_PER_TOKEN
    used, last = 0, start - 1
    for n in range(start, len(units) + 1):
        cost = len(units[n - 1]) + 8
        if last >= start and used + cost > budget:
            break
        used += cost
        last = n
    body = " ".join(f"[¶{n}] {units[n - 1]}" for n in range(start, last + 1))
    return Page(clause.number, clause.title, start, last, len(units), body, last + 1 if last < len(units) else None)


def fragments(edition: Edition, number: str) -> int:
    """How many extracted fragments carry this clause number. More than one means the splitter could not tell a
    heading from a numbered sub-item or a table cell, and `read` returns the first. Callers should say so."""
    connection = _open(edition)
    try:
        row = connection.execute("SELECT count(*) FROM clause WHERE number = ?", (number,)).fetchone()
    finally:
        connection.close()
    return int(row[0])


def sentence(edition: Edition, number: str, para: int) -> str | None:
    clause = read(edition, number)
    units = text.sentences(clause.body) if clause else ()
    return units[para - 1] if 1 <= para <= len(units) else None


def normative_statements(edition: Edition, number: str) -> tuple[tuple[int, str], ...] | None:
    clause = read(edition, number)
    return None if clause is None else text.normative(clause.body)


@dataclass(frozen=True)
class Links:
    number: str
    clauses: tuple[str, ...]  # same-document clauses this one points at that actually exist
    unresolved: tuple[str, ...]  # pointed at but not found in the index: extraction gap, or a cross-document ref
    recommendations: tuple[str, ...]
    standards: tuple[str, ...]
    cited_by: tuple[str, ...]


def links(edition: Edition, number: str) -> Links | None:
    """Outgoing references of a clause, and the clauses of the same edition that point back at it."""
    connection = _open(edition)
    try:
        rows = connection.execute("SELECT number, body FROM clause ORDER BY rowid").fetchall()
    finally:
        connection.close()
    known = {row[0] for row in rows}
    body = next((row[1] for row in rows if row[0] == number), None)
    if body is None:
        return None
    found = text.refs(body)
    back = tuple(n for n, b in rows if n != number and number in text.refs(b).clauses)
    return Links(
        number=number,
        clauses=tuple(c for c in found.clauses if c in known),
        unresolved=tuple(c for c in found.clauses if c not in known),
        recommendations=found.recommendations,
        standards=found.standards,
        cited_by=back,
    )


def grep(
    edition: Edition, pattern: str, *, max_tokens: int = 2000, context: int = 120
) -> tuple[list[dict[str, str]], bool]:
    """Regex over clause bodies in ONE query, with an excerpt around the first match, cut to a token budget.

    Returns (hits, truncated). `truncated` is True when the budget stopped the listing, so a short list is
    distinguishable from a complete one.
    """
    import re

    compiled = re.compile(pattern, re.IGNORECASE)
    connection = _open(edition)
    try:
        rows = connection.execute("SELECT number, body FROM clause ORDER BY rowid").fetchall()
    finally:
        connection.close()
    budget, used = max(max_tokens, 1) * CHARS_PER_TOKEN, 0
    hits: list[dict[str, str]] = []
    for number, body in rows:
        match = compiled.search(body)
        if not match:
            continue
        excerpt = body[max(match.start() - context, 0) : match.end() + context]
        cost = len(excerpt) + len(number) + 20
        if hits and used + cost > budget:
            return hits, True
        used += cost
        hits.append({"number": number, "excerpt": excerpt})
    return hits, False


def top_level(edition: Edition, depth: int = 2) -> tuple[tuple[str, str], ...]:
    """Clauses whose number has at most `depth` dotted components: the shape of the document, not its detail."""
    return tuple((n, t) for n, t in outline(edition) if n.count(".") + 1 <= depth)
