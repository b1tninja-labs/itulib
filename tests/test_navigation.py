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
