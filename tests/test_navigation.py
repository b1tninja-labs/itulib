"""Segmenting, references, citations and budgets, over invented text (never ITU text, never the corpus)."""

from __future__ import annotations

from pathlib import Path

import pytest

from itulib import corpus, index, text
from itulib.sources import Edition

SYNTHETIC = Edition(
    key="T.0#0000-00",
    rec="T.0",
    edition="00/0000",
    title="Synthetic",
    status="test",
    artifact="none",
    sha256="",
    octets=0,
)

LONG = " ".join(f"Gadget number {n} shall be painted blue." for n in range(1, 41))
PAGES = [
    "1.1 Widgets are counted whole. A gadget may be skipped; see clause 1.2 and Rec. ITU-T T.9 for more.\n"
    "1.2 Gadgets are ordered by colour. They should be sorted before widgets, as in clause 1.1 and RFC 9999.\n"
    f"1.3 Painting rules. {LONG}\n"
]


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("ITULIB_HOME", str(tmp_path))
    monkeypatch.setattr(text, "pages", lambda _path: PAGES)
    pdf = corpus.pdf_path(SYNTHETIC)
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"edition")
    index.build(SYNTHETIC)
    return tmp_path


def test_sentences_do_not_split_on_abbreviations() -> None:
    parts = text.sentences("Rec. ITU-T X.1 defines it, e.g. this one. Second sentence here. Third.")
    assert parts == ("Rec. ITU-T X.1 defines it, e.g. this one.", "Second sentence here.", "Third.")


def test_normative_picks_obligation_sentences_only() -> None:
    found = text.normative("It is a widget. It shall be blue. Nobody cares. It may be red.")
    assert [n for n, _ in found] == [2, 4]


def test_refs_need_an_introducing_word_so_versions_and_arcs_do_not_count() -> None:
    found = text.refs(
        "Arc 2.5.4.3 is fixed. See clause 8.1.2 and 8.1.3, or §9.4. Rec. ITU-T X.680 and ISO/IEC 8824-1."
    )
    assert found.clauses == ("8.1.2", "8.1.3", "9.4")
    assert "2.5.4.3" not in found.clauses
    assert found.recommendations == ("X.680",)
    assert found.standards == ("ISO/IEC 8824-1",)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("X.690§11.6¶2", ("X.690", "11.6", 2)), ("11.6", (None, "11.6", None)), ("§8.1 ¶3", (None, "8.1", 3))],
)
def test_parse_ref(raw: str, expected: tuple[str | None, str, int | None]) -> None:
    assert text.parse_ref(raw) == expected


def test_parse_ref_rejects_nonsense() -> None:
    with pytest.raises(ValueError, match="not a clause reference"):
        text.parse_ref("banana")


def test_paging_follows_next_and_loses_nothing(home: Path) -> None:
    seen: list[str] = []
    start: int | None = 1
    pages = 0
    while start is not None:
        page = index.page(SYNTHETIC, "1.3", start=start, max_tokens=60)
        assert page is not None
        assert page.first == start
        seen.append(page.text)
        start = page.next
        pages += 1
    assert pages > 1, "a small budget must split a long clause"
    joined = " ".join(seen)
    assert all(f"[¶{n}]" in joined for n in range(1, 42)), "every sentence must appear exactly through paging"
    assert len(joined.split("[¶")) - 1 == 41


def test_a_page_always_makes_progress_even_if_one_sentence_exceeds_the_budget(home: Path) -> None:
    page = index.page(SYNTHETIC, "1.3", start=1, max_tokens=1)
    assert page is not None and page.last >= 1


def test_start_outside_the_clause_is_an_error(home: Path) -> None:
    with pytest.raises(ValueError, match="outside"):
        index.page(SYNTHETIC, "1.1", start=99)


def test_links_resolve_and_report_back_references(home: Path) -> None:
    out = index.links(SYNTHETIC, "1.1")
    assert out is not None
    assert out.clauses == ("1.2",)
    assert out.recommendations == ("T.9",)
    assert out.cited_by == ("1.2",)
    back = index.links(SYNTHETIC, "1.2")
    assert back is not None and back.standards == ("RFC 9999",)


def test_links_reports_unresolved_clause_numbers(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(text, "pages", lambda _p: ["1.1 This points at clause 7.7 which the index does not hold."])
    index.build(SYNTHETIC)
    out = index.links(SYNTHETIC, "1.1")
    assert out is not None and out.unresolved == ("7.7",) and out.clauses == ()


def test_grep_is_budgeted_and_says_when_it_stopped(home: Path) -> None:
    hits, truncated = index.grep(SYNTHETIC, "gadget", max_tokens=10)
    assert len(hits) == 1 and truncated
    hits, truncated = index.grep(SYNTHETIC, "gadget", max_tokens=5000)
    assert len(hits) == 3 and not truncated


def test_citation_comes_from_the_registry() -> None:
    assert index.citation(SYNTHETIC, "1.2", 3) == "Rec. ITU-T T.0 (00/0000) §1.2¶3"
    assert index.citation(SYNTHETIC, "1.2") == "Rec. ITU-T T.0 (00/0000) §1.2"


def test_top_level_keeps_only_shallow_clauses(home: Path) -> None:
    assert [n for n, _ in index.top_level(SYNTHETIC, 2)] == ["1.1", "1.2", "1.3"]


def test_fragments_counts_a_number_the_splitter_could_not_disambiguate(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        text, "pages", lambda _p: ["1.1 The first fragment, long enough.\n1.1 A second fragment, also long enough."]
    )
    index.build(SYNTHETIC)
    assert index.fragments(SYNTHETIC, "1.1") == 2
    assert index.fragments(SYNTHETIC, "9.9") == 0


def test_pointer_numbers_do_not_become_headings() -> None:
    rows = text.clauses(
        "1.1 The first rule applies as in clause 1.2 and continues here. 1.2 The second rule stands alone."
    )
    assert [r.number for r in rows] == ["1.1", "1.2"]


def test_a_title_is_not_cut_at_an_abbreviation() -> None:
    rows = text.clauses("1.1 Rec. ITU-T T.9 defines the widget in full, and this sentence goes on. Next one here.")
    assert rows[0].title.startswith("Rec. ITU-T T.9 defines")


def test_dois_and_history_rows_are_not_clause_numbers() -> None:
    rows = text.clauses(
        "1.0 ITU-T X.1 1994-07-01 11.1002/1000/3046 history row text here.\n1.1 A real clause with a body."
    )
    assert [r.number for r in rows] == ["1.1"]


def test_bare_pointers_count_only_when_the_clause_exists(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        text,
        "pages",
        lambda _p: [
            "1.1 The target clause with enough body text to be indexed.\n"
            "1.2 This is encoded as in 1.1 and also as in 9.9 which does not exist, plus arc 2.5.4 stays out."
        ],
    )
    index.build(SYNTHETIC)
    out = index.links(SYNTHETIC, "1.2")
    assert out is not None and out.clauses == ("1.1",) and out.unresolved == ()
    back = index.links(SYNTHETIC, "1.1")
    assert back is not None and back.cited_by == ("1.2",)


def test_search_tops_up_with_partial_matches_and_marks_them(home: Path) -> None:
    hits, relaxed = index.search_mode(SYNTHETIC, "widgets counted")
    assert relaxed and hits[0].number == "1.1" and hits[0].all_terms
    assert [h.number for h in hits if not h.all_terms] == ["1.2"], "1.2 has only one of the two terms"
    loose, relaxed = index.search_mode(SYNTHETIC, "widgets zeppelin")
    assert relaxed and loose and not any(h.all_terms for h in loose)
    none, relaxed = index.search_mode(SYNTHETIC, "zeppelin dirigible")
    assert none == () and not relaxed


def test_filler_words_are_not_required_terms() -> None:
    assert text.fts_query("encoding for a value of a CHOICE type") == '"encoding" "value" "CHOICE" "type"'
    assert text.fts_query("of the") == '"of" "the"', "a query made only of filler is still a query"


def test_heading_only_parents_expose_their_children(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        text,
        "pages",
        lambda _p: ["1.1.1 First child clause with plenty of body text.\n1.1.2 Second child clause with body text."],
    )
    index.build(SYNTHETIC)
    assert index.read(SYNTHETIC, "1.1") is None
    assert [n for n, _ in index.children(SYNTHETIC, "1.1")] == ["1.1.1", "1.1.2"]
    assert index.children(SYNTHETIC, "7.7") == ()


def test_slice_rows_pages_without_loss_and_always_progresses() -> None:
    rows = tuple((f"1.{n}", "t" * 40) for n in range(1, 60))
    got: list[str] = []
    start: int | None = 0
    while start is not None:
        shown, start = index.slice_rows(rows, start, 40)
        assert shown
        got.extend(n for n, _ in shown)
    assert got == [n for n, _ in rows]
    with pytest.raises(ValueError, match="outside"):
        index.slice_rows(rows, 999, 40)


def test_annex_headings_are_clauses_only_at_a_sentence_boundary() -> None:
    rows = text.clauses(
        "1.1 A normal clause with a body of text. A.1 First annex clause with body text here. "
        "See also D.2 and G.711 which are not headings."
    )
    assert [r.number for r in rows] == ["1.1", "A.1"]


def test_annex_refs_parse_and_link() -> None:
    assert text.parse_ref("X.690§A.1¶2") == ("X.690", "A.1", 2)
    assert text.refs("As specified in clause A.2.3 and C.1.").clauses == ("A.2.3", "C.1")


HEADED = (
    "8 Basic rules\n"
    "8.1 General rules This first rule applies to everything here and carries on for a while.\n"
    "8.1.1 Structure The structure rule says something specific about structure, see 8.1 for more.\n"
    "8.1.2 Lengths\n"
    "8.1.2.1 The length rule is stated in this numbered paragraph with enough words to index.\n"
    "8.1.2.2 The second paragraph carries on with other words, and mentions 8.1.2.1 only by pointer.\n"
    "8.2 Booleans Booleans use one octet and the rule is a short but real sentence of text.\n"
    "Annex A Examples (This annex is informative.) Example text follows here with some words.\n"
    "A.1 First example The first example paragraph holds some more invented words of text.\n"
)
LISTED = [
    ("8", "Basic rules"),
    ("8.1", "General rules"),
    ("8.1.1", "Structure"),
    ("8.1.2", "Lengths"),
    ("8.2", "Booleans"),
    ("A", "Examples"),
    ("A.1", "First example"),
]


def test_listed_headings_give_exact_titles_and_keep_heading_only_parents() -> None:
    rows = {c.number: c for c in text.clauses(HEADED, LISTED)}
    assert rows["8"].title == "Basic rules" and rows["8"].body == ""
    assert rows["8.1.2"].title == "Lengths" and rows["8.1.2"].body == ""
    assert rows["8.1"].body.startswith("This first rule applies")
    assert "A" in rows and rows["A"].title == "Examples"


def test_numbered_paragraphs_are_accepted_only_as_successors() -> None:
    nums = [c.number for c in text.clauses(HEADED, LISTED)]
    assert "8.1.2.1" in nums and "8.1.2.2" in nums
    assert nums.count("8.1") == 1, "the pointer 'see 8.1' must not create a second 8.1"
    assert nums.count("8.1.2.1") == 1, "the pointer to 8.1.2.1 must not create a second one"


def test_a_pointer_that_matches_a_listed_number_is_not_its_heading() -> None:
    text_with_pointer = "See 8.1 General rules for details. 8.1 General rules The real heading text goes here for it."
    rows = text.clauses(text_with_pointer, [("8.1", "General rules")])
    assert [c.number for c in rows] == ["8.1"]
    assert rows[0].body.startswith("The real heading text")


def _by_number(source: str, listed: list[tuple[str, str]]) -> dict[str, text.Clause]:
    return {c.number: c for c in text.clauses(source, listed)}


def test_an_acronym_before_a_heading_is_not_the_word_per() -> None:
    # "PER" is an encoding-rules acronym; lowercased it is the preposition "per", which introduces pointers.
    rows = _by_number(
        "10 The approach used for PER 10.1 Use of the notation 10.1.1 These rules make use of the notation at hand.",
        [("10", "The approach used for PER"), ("10.1", "Use of the notation")],
    )
    assert "10.1" in rows and rows["10.1"].heading
    assert "10.1.1" in rows
    # the real word still introduces a pointer
    assert text.refs("Charged per 8.1.2 of the schedule.").bare == ("8.1.2",)


def test_a_heading_right_after_a_title_ending_in_a_pointer_word_is_still_a_heading() -> None:
    rows = _by_number(
        "15 The gadget clause 15.1 Generated parts 15.1.1 The first rule concerns the generated parts at length.",
        [("15", "The gadget clause"), ("15.1", "Generated parts")],
    )
    assert rows["15.1"].heading and "15.1.1" in rows


def test_a_number_that_is_a_located_heading_elsewhere_is_not_also_a_paragraph() -> None:
    # A list of productions with their clause numbers precedes the clauses themselves.
    source = (
        "16 Structures The structures are defined in the following clauses: "
        "AlphaStructureProduction 16.1 BetaStructureProduction 16.2 GammaStructureProduction 16.3 "
        "16.1 Alpha encoding 16.1.1 The alpha rule is stated here with enough words to be kept. "
        "16.2 Beta encoding 16.2.1 The beta rule is stated here with enough words to be kept."
    )
    listed = [("16", "Structures"), ("16.1", "Alpha encoding"), ("16.2", "Beta encoding")]
    numbers = [c.number for c in text.clauses(source, listed)]
    assert numbers.count("16.1") == 1 and numbers.count("16.2") == 1
    assert "16.3" not in numbers
    rows = _by_number(source, listed)
    assert rows["16.1"].heading and rows["16.2"].heading


def test_a_pointer_followed_by_a_function_word_does_not_take_the_place_of_the_paragraph() -> None:
    source = (
        "13 Tables 13.1 The first rule is long enough to be a paragraph. "
        "13.2 The second rule is the result of applying 13.3 to the set containing one thing. "
        "13.3 The third rule is the real one and carries its own words."
    )
    rows = _by_number(source, [("13", "Tables")])
    assert rows["13.3"].body.startswith("The third rule")
    assert "13.3 to the set" in rows["13.2"].body


def test_definition_entries_with_lowercase_terms_are_still_paragraphs() -> None:
    source = (
        "3 Definitions 3.1 canonical form: a form chosen to be unique among all possible forms. "
        "3.2 data value: information specified as the value of some type in the notation."
    )
    assert [c.number for c in text.clauses(source, [("3", "Definitions")])] == ["3", "3.1", "3.2"]


ANNEXED = (
    "5 Last clause 5.1 The final rule of the last clause is long enough to be kept. "
    "Annex A Useful things (This annex forms an integral part of this Recommendation.) "
    "A.1 This annex specifies something that is useful in practice. A.2 The second annex rule has words as well. "
    "Annex B Notes (This annex does not form an integral part of this Recommendation.) "
    "Annex C Samples (This annex does not form an integral part of this Recommendation.) "
    "A preamble sentence that is not numbered. C.1 The first sample paragraph has enough words to be kept."
)


def test_annex_paragraphs_are_found_when_the_bookmarks_skip_the_annex_heading() -> None:
    numbers = [c.number for c in text.clauses(ANNEXED, [("5", "Last clause")])]
    # B has no numbered paragraphs and is skipped; the preamble before C.1 does not stop it either.
    assert numbers == ["5", "5.1", "A.1", "A.2", "C.1"]


def test_an_annex_shaped_number_without_the_annex_heading_is_not_a_paragraph() -> None:
    source = "5 Last clause 5.1 The final rule of the last clause is long enough. C.1 Looks like an annex paragraph."
    assert [c.number for c in text.clauses(source, [("5", "Last clause")])] == ["5", "5.1"]


def test_a_number_glued_to_the_next_word_is_still_a_paragraph() -> None:
    source = "22 Encoding 22.1 Actions 22.1.1If the thing is set, then the encoder acts on it as described."
    assert "22.1.1" in _by_number(source, [("22", "Encoding"), ("22.1", "Actions")])


def test_pointers_qualified_by_another_recommendation_are_foreign() -> None:
    found = text.refs(
        "Defined in Rec. ITU-T T.998 | ISO/IEC 9998-1, clause 12.3, and in clause 4.5. "
        "Also clause 7.2 of Rec. ITU-T T.997, and see Rec. ITU-T T.998 | ISO/IEC 9998-1, 3.8.27."
    )
    assert found.clauses == ("4.5",)
    assert set(found.foreign) == {"12.3", "7.2"}
    assert "3.8.27" not in found.bare


def test_clauses_without_a_listing_fall_back_to_the_heuristic() -> None:
    assert [c.number for c in text.clauses("1.1 A clause with enough body text to be kept as one.")] == ["1.1"]


def test_headings_fall_back_to_contents_lines_when_there_are_no_bookmarks(tmp_path: Path) -> None:
    fake = tmp_path / "x.pdf"
    fake.write_bytes(b"not a pdf")
    contents = ["8.1 General rules ........ 12", "8.1.2 Lengths ........ 13", "Annex A line without leaders"]
    assert text.headings(fake, contents) == [("8.1", "General rules"), ("8.1.2", "Lengths")]


def test_parse_ref_accepts_bare_top_level_numbers() -> None:
    assert text.parse_ref("X.690 8") == ("X.690", "8", None)
    assert text.parse_ref("X.690§A") == ("X.690", "A", None)


def test_a_real_heading_outranks_a_body_that_merely_repeats_the_word(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        text,
        "pages",
        lambda _p: [
            "2 Gadgets Short body about nothing much at all in here.\n"
            "3 Other things Gadgets gadgets gadgets gadgets gadgets are mentioned in this body again and again."
        ],
    )
    monkeypatch.setattr(text, "headings", lambda _p, _t=None: [("2", "Gadgets"), ("3", "Other things")])
    index.build(SYNTHETIC)
    hits, _ = index.search_mode(SYNTHETIC, "gadgets")
    assert hits[0].number == "2", "the clause whose HEADING is the word must come first"


def test_an_index_from_an_older_schema_is_refused_with_the_remedy(home: Path) -> None:
    import sqlite3

    db = index._db_path(SYNTHETIC)
    with sqlite3.connect(db) as connection:
        connection.execute("UPDATE meta SET value = '1' WHERE key = 'schema'")
    with pytest.raises(RuntimeError, match="older itulib"):
        index.search(SYNTHETIC, "widgets")


OTHER = Edition(
    key="T.0#1111-11",
    rec="T.0",
    edition="11/1111",
    title="Synthetic, later",
    status="test",
    artifact="none",
    sha256="",
    octets=0,
)


def _build_two(monkeypatch: pytest.MonkeyPatch, old_pages: list[str], new_pages: list[str]) -> None:
    for edition, pages in ((SYNTHETIC, old_pages), (OTHER, new_pages)):
        monkeypatch.setattr(text, "pages", lambda _p, pages=pages: pages)
        pdf = corpus.pdf_path(edition)
        pdf.parent.mkdir(parents=True, exist_ok=True)
        pdf.write_bytes(edition.key.encode())
        index.build(edition)


def test_compare_ignores_extraction_noise_and_reports_real_changes(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    old = [
        "1.1 The encoding shall appear in a ppear order. Each unit is counted.\n"
        "1.2 All of the gadgets are painted red.\n"
    ]
    new = [
        "1.1 The encoding shall appear in appear order. Each unit is counted.\n"
        "1.2 All of the gadgets are painted blue.\n"
    ]
    _build_two(monkeypatch, old, new)
    same = index.compare(SYNTHETIC, OTHER, "1.1")
    assert same.same and same.in_a and same.in_b, "a split word and nothing else is not a change"
    changed = index.compare(SYNTHETIC, OTHER, "1.2")
    assert not changed.same
    assert [s for _, s in changed.removed] == ["All of the gadgets are painted red."]
    assert [s for _, s in changed.added] == ["All of the gadgets are painted blue."]


def test_compare_says_when_a_clause_exists_in_only_one_edition(home: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _build_two(
        monkeypatch,
        ["1.1 A clause that exists in the old edition only, with words."],
        ["1.2 A clause that exists in the new edition only, with words."],
    )
    result = index.compare(SYNTHETIC, OTHER, "1.1")
    assert result.in_a and not result.in_b and not result.same


def test_compare_of_a_clause_in_neither_edition_is_not_reported_as_unchanged(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _build_two(
        monkeypatch, ["1.1 Some clause with enough words in it."], ["1.1 Some clause with enough words in it."]
    )
    result = index.compare(SYNTHETIC, OTHER, "9.9")
    assert not result.in_a and not result.in_b and not result.same
