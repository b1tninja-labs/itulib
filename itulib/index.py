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
from .sources import Edition


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
