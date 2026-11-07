"""A full-text index over one edition, tagged with the digest it was built from.

The index records the sha256 of the PDF it came from and refuses to serve results when the corpus no longer
matches. That is the difference between "this clause says X in the edition you hold" and a stale table that
reports the same confident answer after ITU republished something - a gate that silently skips, in the shape
of a search result.
"""

from __future__ import annotations

import dataclasses
import hashlib
import pathlib
import re
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
    all_terms: bool = True  # False: matched only some of the query's terms


def _db_path(edition: Edition) -> pathlib.Path:
    return corpus.home() / "index" / f"{edition.key.replace('#', '-')}.sqlite3"


def build(edition: Edition) -> int:
    """(Re)build the index for one edition. Returns the clause count."""
    pdf = corpus.require(edition)
    digest = hashlib.sha256(pdf.read_bytes()).hexdigest()
    extracted = text.pages(pdf)
    rows = text.clauses(extracted, text.headings(pdf, extracted))
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
            CREATE VIRTUAL TABLE clause USING fts5(number, title UNINDEXED, head, body, tokenize='porter unicode61');
            """
        )
        connection.executemany(
            "INSERT INTO clause (number, title, head, body) VALUES (?, ?, ?, ?)",
            [(row.number, row.title, row.title if row.heading else "", row.body) for row in rows],
        )
        connection.executemany(
            "INSERT INTO meta (key, value) VALUES (?, ?)",
            [("edition", edition.key), ("pdf_sha256", digest), ("clauses", str(len(rows))), ("schema", SCHEMA)],
        )
        connection.commit()
    finally:
        connection.close()
    return len(rows)


def _open(edition: Edition) -> sqlite3.Connection:
    db = _db_path(edition)
    if not db.is_file():
        raise corpus.CorpusMissing(
            f"{edition.key}: no index. Run: itulib fetch {edition.key} && itulib index {edition.key} "
            f"(or: itulib sync)"
        )
    connection = sqlite3.connect(db)
    meta = dict(connection.execute("SELECT key, value FROM meta"))
    if meta.get("schema") != SCHEMA:
        connection.close()
        raise RuntimeError(
            f"{edition.key}: the index was built by an older itulib. "
            f"Run: itulib index {edition.key} (or: itulib sync)"
        )
    pdf = corpus.require(edition)
    if meta.get("pdf_sha256") != hashlib.sha256(pdf.read_bytes()).hexdigest():
        connection.close()
        raise RuntimeError(
            f"{edition.key}: the corpus changed since the index was built. Run: itulib index {edition.key}"
        )
    return connection


def search(edition: Edition, query: str, limit: int = 8) -> tuple[Hit, ...]:
    return search_mode(edition, query, limit)[0]


def search_mode(edition: Edition, query: str, limit: int = 8) -> tuple[tuple[Hit, ...], bool]:
    """(hits, relaxed). Every term must match first; if that finds nothing the terms are OR-ed, and `relaxed`
    says so, because "some of your words matched" is a weaker answer than "all of them did" and the caller
    should be able to tell which one it is holding."""
    strict = _match(edition, text.fts_query(query), limit)
    if len(strict) >= limit or len(query.split()) < 2:
        return strict, False
    seen = {hit.number for hit in strict}
    extra = tuple(
        dataclasses.replace(hit, all_terms=False)
        for hit in _match(edition, text.fts_query(query, any_term=True), limit + len(strict))
        if hit.number not in seen
    )
    merged = (*strict, *extra)[:limit]
    return merged, len(merged) > len(strict)


def _match(edition: Edition, prepared: str, limit: int) -> tuple[Hit, ...]:
    connection = _open(edition)
    try:
        # BM25_WEIGHTS is a module constant, never user input.
        cursor = connection.execute(
            f"SELECT number, title, snippet(clause, 3, '', '', ' … ', 24), bm25(clause, {BM25_WEIGHTS}) FROM clause "  # noqa: S608
            f"WHERE clause MATCH ? ORDER BY bm25(clause, {BM25_WEIGHTS}) LIMIT ?",
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
# bm25 column weights for (number, title, body). Titles are the document's own headings, so a title match is a much
# stronger signal than the same word somewhere in a body.
BM25_WEIGHTS = "2.0, 0.0, 15.0, 1.0"  # number, title (display only), head, body
SCHEMA = "2"


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
    if not clause.body:
        return Page(clause.number, clause.title, 1, 0, 0, "", None)
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
    back = tuple(n for n, b in rows if n != number and _points_at(b, number))
    return Links(
        number=number,
        clauses=tuple(c for c in (*found.clauses, *found.bare) if c in known and c != number),
        unresolved=tuple(c for c in found.clauses if c not in known),
        recommendations=tuple(r for r in found.recommendations if r != edition.rec),
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


def _points_at(body: str, number: str) -> bool:
    found = text.refs(body)
    return number in found.clauses or number in found.bare


def slice_rows(
    rows: tuple[tuple[str, str], ...], start: int, max_tokens: int
) -> tuple[tuple[tuple[str, str], ...], int | None]:
    """(rows[start:...], next start or None), cut to a token budget. Always returns at least one row."""
    if not 0 <= start <= len(rows):
        raise ValueError(f"start={start} is outside 0..{len(rows)}")
    budget, used, end = max(max_tokens, 1) * CHARS_PER_TOKEN, 0, start
    while end < len(rows):
        cost = len(rows[end][0]) + len(rows[end][1]) + 12
        if end > start and used + cost > budget:
            break
        used += cost
        end += 1
    return rows[start:end], (end if end < len(rows) else None)


@dataclass(frozen=True)
class Comparison:
    number: str
    in_a: bool
    in_b: bool
    same: bool
    removed: tuple[tuple[int, str], ...]  # (¶ in edition a, sentence) present only in a
    added: tuple[tuple[int, str], ...]  # (¶ in edition b, sentence) present only in b


def _sentence_key(sentence: str) -> str:
    """What two sentences must share to count as the same across editions.

    The extractor splits words differently in different editions ("a ppear"), drops mathematical symbols from some
    ("M ≠ M'" loses its sign) and the editions cite each other in a different order ("ITU-T Rec. X.680" became
    "Rec. ITU-T X.680"). So matching ignores case, whitespace, punctuation and symbols. The cost is stated in the
    docstring of `compare`: a change that consists only of a symbol or punctuation mark is invisible.
    """
    return re.sub(r"[\W_]+", "", sentence.replace("ITU-T Rec.", "Rec. ITU-T")).casefold()


def compare(a: Edition, b: Edition, number: str) -> Comparison:
    """What changed in clause `number` between two editions, by sentence.

    Numbering can differ between editions, so a clause that exists in only one is reported as such rather than
    as a deletion: the rule may simply have moved. Matching is by sentence, so a reworded sentence appears as one
    removed and one added. Matching ignores punctuation and symbols (see `_sentence_key`), so a change consisting
    only of a symbol, such as a sign or a comparison operator, is NOT reported: check the PDF when that matters.
    """
    import difflib

    clause_a, clause_b = read(a, number), read(b, number)
    sa = text.sentences(clause_a.body) if clause_a and clause_a.body else ()
    sb = text.sentences(clause_b.body) if clause_b and clause_b.body else ()
    keys_a, keys_b = [_sentence_key(s) for s in sa], [_sentence_key(s) for s in sb]
    matcher = difflib.SequenceMatcher(a=keys_a, b=keys_b, autojunk=False)
    removed: list[tuple[int, str]] = []
    added: list[tuple[int, str]] = []
    for op, a0, a1, b0, b1 in matcher.get_opcodes():
        if op in {"delete", "replace"}:
            removed += [(n + 1, sa[n]) for n in range(a0, a1)]
        if op in {"insert", "replace"}:
            added += [(n + 1, sb[n]) for n in range(b0, b1)]
    return Comparison(
        number,
        clause_a is not None,
        clause_b is not None,
        clause_a is not None and clause_b is not None and not removed and not added,
        tuple(removed),
        tuple(added),
    )


def children(edition: Edition, number: str) -> tuple[tuple[str, str], ...]:
    """The nearest descendants of a clause that has no body of its own. Heading-only clauses ("8.1.2 Identifier
    octets") are not indexed, so `read` would otherwise say "no clause" about a clause that plainly exists."""
    below = [(n, t) for n, t in outline(edition) if n.startswith(number + ".")]
    if not below:
        return ()
    shallowest = min(n.count(".") for n, _ in below)
    return tuple(row for row in below if row[0].count(".") == shallowest)


def top_level(edition: Edition, depth: int = 2) -> tuple[tuple[str, str], ...]:
    """Clauses whose number has at most `depth` dotted components: the shape of the document, not its detail."""
    return tuple((n, t) for n, t in outline(edition) if n.count(".") + 1 <= depth)
