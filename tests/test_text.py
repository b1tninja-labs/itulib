"""Clause splitting, tested on synthetic text.

No recommendation prose appears in this file on purpose: the extractor's behaviour can be pinned with made-up
clauses, and doing so keeps the repository free of ITU text. The shapes below are the ones the real 02/2021
edition actually produces, including the dot-leader contents lines and the `ITU -T` spacing artefact.
"""

from __future__ import annotations

import pytest

from itulib import text

SYNTHETIC = """
CONTENTS
11.1 Boolean values .................... 20
11.2 Unused bits ....................... 20
7 Conformance
7.1 Dynamic conformance is specified by clauses 8 to 12 inclusive.
8.2 Encoding of a boolean value
8.2.1 The encoding of a boolean value shall be primitive. The contents octets shall consist of a single
octet, and are therefore strongly urged to consult the appropriate Rec. ITU -T databases for details.
8.2.2 If the boolean value is FALSE the octet shall be zero, and this sentence is long enough to be kept.
11.1 Boolean values
11.1.1 If the encoding represents the boolean value TRUE, its single contents octet shall have all eight
bits set to one, which is a rule about DER that a decoder has to enforce on every certificate it accepts.
"""


def test_dot_leaders_are_dropped_rather_than_indexed() -> None:
    clauses = text.clauses(SYNTHETIC)
    numbers = [clause.number for clause in clauses]
    assert "11.2" not in numbers, "a contents entry was indexed as though it were a rule"
    assert not any("...." in clause.body for clause in clauses)


def test_real_clauses_are_found_with_their_numbers() -> None:
    clauses = text.clauses(SYNTHETIC)
    found = {clause.number for clause in clauses}
    assert "8.2.1" in found
    assert "11.1.1" in found


def test_a_clause_cites_with_edition_and_number() -> None:
    clause = text.find(text.clauses(SYNTHETIC), "11.1.1")
    assert clause is not None
    assert clause.cite("X.690#2021-02") == "Rec. ITU-T X.690#2021-02 §11.1.1"
    assert "eight" in clause.body


def test_tidy_repairs_the_observed_spacing_artefact_and_says_nothing_else() -> None:
    assert "Rec. ITU-T databases" in text.tidy("Rec. ITU -T databases")
    assert text.tidy("a   b\n  c") == "a b c"


def test_hyphenated_queries_survive_the_search_sanitiser() -> None:
    """`set-of` is a term, not `set` NOT `of`. Unquoted, FTS5 raises and the tool crashes."""
    prepared = text.fts_query("set-of value order")
    assert prepared == '"set-of" "value" "order"'


def test_quotes_in_a_query_are_escaped_not_interpreted() -> None:
    assert text.fts_query('say "hello"') == '"say" """hello"""'


def test_an_empty_query_is_refused_rather_than_matching_everything() -> None:
    """An empty MATCH is not "no results" in FTS5, and a search that hands back the whole corpus on a blank
    input looks like a working search to whoever wrote the caller."""
    with pytest.raises(ValueError):
        text.fts_query("   ")


def test_bodyless_headings_are_not_indexed() -> None:
    """A heading whose body is a page number is a contents entry, and indexing it answers nothing."""
    clauses = text.clauses("9.1 Some heading 42\n9.2 Another heading with a body long enough to survive here")
    assert [clause.number for clause in clauses] == ["9.2"]
