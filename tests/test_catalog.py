"""The catalogue crawler, over invented pages shaped like the ones read from itu.int on 2026-11-07.

No page here is ITU's: titles and numbers are made up, so these run offline and `tests/test_license.py` has
nothing to object to. The real pages were checked by hand against the same parsers (756 listings in series X,
34 components for one recommendation, five assets for one edition); that check cannot be a test.
"""

# ruff: noqa: E501  (the fixtures are HTML pages; their long lines are the point)

from __future__ import annotations

import json
import urllib.request
from pathlib import Path

import pytest

from itulib import catalog, cli, corpus

SERIES_PAGE = """
<table>
<tr><td>x</td><td>header</td></tr>
<tr><td width="5%"><p><a href="./recommendation.asp?lang=en&amp;parent=T-REC-Z.10"><strong>Z.10</strong></a></p></td>
<td style="color:#000"><p>Widget interchange framework �<font color="red"> </font></p></td></tr>
<tr><td width="5%"><p><a href="./recommendation.asp?lang=en&amp;parent=T-REC-Z.11bis"><strong>Z.11bis</strong></a></p></td>
<td style="font-style:italic"><p><font color="red">[Withdrawn] </font>Old gadget routing �<font color="red"><br>Deleted as covered by Z.10</font></p></td></tr>
<tr><td><a href="./recommendation.asp?lang=en&amp;parent=T-REC-Z.10-200001-I"><strong>Z.10 (01/00)</strong></a></td>
<td>a component row that must not be listed as a recommendation</td></tr>
</table>
"""

RECOMMENDATION_PAGE = """
<table>
<tr><td colspan="3"><center><strong>In force components </strong></center></td></tr>
<tr><td nowrap><a href="./recommendation.asp?lang=en&amp;parent=T-REC-Z.10-202001-I"><strong>Z.10 (01/20)</strong></a></td>
<td>Widget interchange framework</td><td nowrap>In force <br></td></tr>
<tr><td nowrap><a href="./recommendation.asp?lang=en&amp;parent=T-REC-Z.10-202101-I!Cor1"><strong>Z.10 (2020) Corrigendum 1 (01/21)</strong></a></td>
<td> </td><td nowrap>In force <br></td></tr>
<tr><td nowrap><a href="./recommendation.asp?lang=en&amp;parent=T-REC-Z.10-202607-P!Cor2"><strong>Z.10 (2020) Corrigendum 2 (07/26)</strong></a></td>
<td> </td><td nowrap>In force (prepublished)<br></td></tr>
<tr><td nowrap><a href="./recommendation.asp?lang=en&amp;parent=T-REC-Z.1-Z.9-202001-I"><strong>Z.1-Z.9 (01/20)</strong></a></td>
<td>collective file</td><td nowrap>In force <br></td></tr>
<tr><td colspan="3"><center><strong>Superseded and Withdrawn components </strong></center></td></tr>
<tr><td nowrap><a href="./recommendation.asp?lang=en&amp;parent=T-REC-Z.10-199901-S"><strong>Z.10 (01/99)</strong></a></td>
<td>Widget interchange</td><td nowrap><font color="red">Superseded </font><br></td></tr>
<tr><td nowrap><a href="./recommendation.asp?lang=en&amp;parent=T-REC-Z.10-199901-S!Amd1"><strong>Z.10 (1999) Amendment 1</strong></a></td>
<td> </td><td nowrap><font color="red">Superseded </font><br></td></tr>
</table>
"""

COMPONENT_PAGE = """
<html><head><title>Z.10 : Widget interchange framework</title></head><body>
<p>Recommendation Z.10 (01/20) Approved in 2020-01-14 Status : In force</p>
<table><tr><td colspan="2"><p><strong>Access : Freely available items</strong></p></td></tr>
<table>
<tr><td>English</td><td>EPUB</td><td>23249231 bytes</td><td>2020-02-12</td><td>E 1</td>
<td><a href="https://www.itu.int/rec/dologin_pub.asp?lang=e&amp;id=T-REC-Z.10-202001-I!!EPB-E&amp;type=items"><img alt="Download"></a></td></tr>
<tr><td>English</td><td>PDF (acrobat)</td><td>3581573 bytes</td><td>2019-12-20</td>
<td><a href="https://www.itu.int/rec/dologin_pub.asp?lang=e&amp;id=T-REC-Z.10-202001-I!!PDF-E&amp;type=items"><img alt="Download"></a></td></tr>
<tr><td>French</td><td>PDF (acrobat)</td><td>111 bytes</td><td>2019-12-21</td>
<td><a href="https://www.itu.int/rec/dologin_pub.asp?lang=f&amp;id=T-REC-Z.10-202001-I!!PDF-F&amp;type=items"><img alt="Download"></a></td></tr>
</table></table>
<table><tr><td nowrap><p><strong>Access : </strong></p></td>
<td nowrap><p><strong><a href="http://www.itu.int/TIES">TIES users</a></strong></p></td></tr>
<table>
<tr><td>English</td><td>Word 2007</td><td>2525635 bytes</td><td>2019-12-20</td>
<td><a href="https://www.itu.int/rec/dologin_pub.asp?lang=e&amp;id=T-REC-Z.10-202001-I!!MSW-E&amp;type=items
 "><img alt="Download"></a></td></tr>
</table></table>
<a href="/dms_pubrec/itu-t/rec/z/T-REC-Z.10-202001-I!!TOC-HTM-E.htm">Table of Contents</a>
<a href="/dms_pubrec/itu-t/rec/z/T-REC-Z.10-202001-I!!SUM-HTM-E.htm">Summary</a>
</body></html>
"""


def test_series_listing_gives_recommendations_with_status_and_skips_component_rows() -> None:
    listings = catalog.parse_series(SERIES_PAGE)
    assert [item.rec for item in listings] == ["Z.10", "Z.11bis"]
    assert listings[0].status == "active" and listings[0].title == "Widget interchange framework"
    assert listings[1].status == "withdrawn"
    assert listings[1].title == "Old gadget routing"
    assert listings[1].note == "Deleted as covered by Z.10"


def test_recommendation_page_lists_components_by_section_and_kind() -> None:
    comps = {c.id: c for c in catalog.parse_recommendation(RECOMMENDATION_PAGE)}
    assert comps["T-REC-Z.10-202001-I"].kind == "edition" and comps["T-REC-Z.10-202001-I"].section == "in force"
    assert comps["T-REC-Z.10-202101-I!Cor1"].kind == "corrigendum"
    assert comps["T-REC-Z.10-202607-P!Cor2"].status == "in force (prepublished)"
    assert comps["T-REC-Z.1-Z.9-202001-I"].kind == "collection"
    assert (
        comps["T-REC-Z.10-199901-S"].section == "superseded" and comps["T-REC-Z.10-199901-S"].status == "superseded"
    )
    assert comps["T-REC-Z.10-199901-S!Amd1"].kind == "amendment"
    assert comps["T-REC-Z.10-202001-I"].label == "Z.10 (01/20)"


def test_component_page_assets_carry_format_size_date_and_access() -> None:
    page = catalog.parse_component(COMPONENT_PAGE, "T-REC-Z.10-202001-I")
    assert page.status == "in force" and page.approved == "2020-01-14"
    by = {(a.fmt, a.lang): a for a in page.assets}
    assert by[("EPB", "E")].size == 23249231 and by[("EPB", "E")].posted == "2020-02-12"
    assert by[("EPB", "E")].access == "free"
    assert by[("PDF", "E")].size == 3581573 and by[("PDF", "F")].size == 111
    word = by[("MSW", "E")]
    assert word.access == "ties", "the word text outside the <strong> tag decides the access class"
    assert word.size == 2525635 and word.url.endswith("&type=items"), "trailing whitespace in the href is stripped"
    assert by[("TOC-HTM", "E")].url.startswith("https://www.itu.int/dms_pubrec/")
    assert by[("SUM-HTM", "E")].access == "free"


def test_component_ids_with_a_single_bang_still_yield_formats() -> None:
    link = "https://www.itu.int/rec/dologin_pub.asp?lang=e&amp;id=T-REC-Z.10-202109-I!Err1!PDF-E&amp;type=items"
    assets = catalog.parse_component(f'<a href="{link}">x</a>', "T-REC-Z.10-202109-I!Err1").assets
    assert [(a.fmt, a.lang) for a in assets] == [("PDF", "E")], "errata use !Err1!PDF-E, not !!PDF-E"


def test_best_source_prefers_epub_then_pdf_and_never_word() -> None:
    page = catalog.parse_component(COMPONENT_PAGE, "x")
    component: dict[str, object] = {"assets": [vars(a) for a in page.assets]}
    best = catalog.best_source(component)
    assert best["primary"] is best["epub"] and best["pdf"] and best["toc"] and best["summary"]
    no_epub: dict[str, object] = {"assets": [vars(a) for a in page.assets if a.fmt != "EPB"]}
    assert catalog.best_source(no_epub)["primary"] is not None
    only_word: dict[str, object] = {"assets": [vars(a) for a in page.assets if a.fmt == "MSW"]}
    assert catalog.best_source(only_word)["primary"] is None, "TIES-only Word is never a source"


# --- fetcher ----------------------------------------------------------------------------------------------


class Clock:
    def __init__(self) -> None:
        self.now = 100.0
        self.slept: list[float] = []

    def monotonic(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def make_fetcher(tmp_path: Path, clock: Clock, pages: dict[str, bytes]) -> tuple[catalog.Fetcher, list[str]]:
    calls: list[str] = []

    def opener(request: urllib.request.Request) -> bytes:
        calls.append(request.full_url)
        assert request.get_header("User-agent", "").startswith("itulib-catalog/"), "must identify itself"
        return pages[request.full_url]

    return catalog.Fetcher(tmp_path, opener=opener, sleep=clock.sleep, clock=clock.monotonic), calls


def test_fetcher_waits_between_requests_and_caches_on_disk(tmp_path: Path) -> None:
    clock = Clock()
    a, b = f"{catalog.BASE}/rec/T-REC-Z/en", f"{catalog.BASE}/rec/T-REC-Y/en"
    fetcher, calls = make_fetcher(tmp_path, clock, {a: b"one", b: b"two"})
    assert fetcher.get(a) == "one"
    assert clock.slept == [], "the first request needs no wait"
    assert fetcher.get(b) == "two"
    assert clock.slept == [pytest.approx(1.0)], "the second waits out the interval"
    assert fetcher.get(a) == "one" and calls == [a, b], "a cached page makes no request"
    fetcher.get(a, refresh=True)
    assert calls == [a, b, a]


def test_fetcher_reads_only_paths_robots_txt_allows() -> None:
    fetcher = catalog.Fetcher(None, opener=lambda _r: b"")
    for url in (
        f"{catalog.BASE}/itudocs/x",
        f"{catalog.BASE}/cgi-bin/x",
        "https://example.com/rec/x",
        f"{catalog.BASE}/dms_priv/x",
    ):
        with pytest.raises(ValueError, match="only /rec/ and /dms_pubrec/"):
            fetcher.get(url)


def test_decode_falls_back_to_cp1252_instead_of_failing() -> None:
    assert catalog.decode("café".encode("cp1252")) == "café"
    assert catalog.decode("café".encode()) == "café"


# --- sync and manifest -------------------------------------------------------------------------------------


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("ITULIB_HOME", str(tmp_path / "home"))
    return tmp_path


def site(extra: dict[str, bytes] | None = None) -> dict[str, bytes]:
    base = catalog.BASE
    pages = {
        f"{base}/rec/T-REC-Z/en": SERIES_PAGE.encode("utf-8"),
        f"{base}/rec/T-REC-Z.10/en": RECOMMENDATION_PAGE.encode("utf-8"),
        f"{base}/rec/T-REC-Z.10-202001-I/en": COMPONENT_PAGE.encode("utf-8"),
        f"{base}/rec/T-REC-Z.10-202101-I!Cor1/en": COMPONENT_PAGE.encode("utf-8"),
        f"{base}/rec/T-REC-Z.10-202607-P!Cor2/en": COMPONENT_PAGE.encode("utf-8"),
    }
    pages.update(extra or {})
    return pages


def test_sync_listing_then_details_is_resumable_and_skips_withdrawn(home: Path) -> None:
    fetcher, calls = make_fetcher(home / "cache", Clock(), site())
    assert catalog.sync_listing("Z", fetcher) == 2
    done, pages = catalog.sync_details("Z", fetcher)
    assert (done, pages) == (1, 3), "Z.11bis is withdrawn and skipped; only the three in-force components are read"
    assert not any("Z.11bis" in c for c in calls)
    before = len(calls)
    assert catalog.sync_details("Z", fetcher) == (0, 0), "details already present: nothing is requested again"
    assert len(calls) == before
    recs = catalog.load("Z")
    assert recs["Z.10"]["components"] and recs["Z.11bis"].get("components") is None


def test_sync_listing_keeps_details_and_refuses_an_empty_parse(home: Path) -> None:
    fetcher, _ = make_fetcher(home / "cache", Clock(), site())
    catalog.sync_listing("Z", fetcher)
    catalog.sync_details("Z", fetcher)
    catalog.sync_listing("Z", fetcher, refresh=True)
    assert catalog.load("Z")["Z.10"]["components"], "re-listing must not discard fetched details"
    empty, _ = make_fetcher(home / "cache2", Clock(), {f"{catalog.BASE}/rec/T-REC-Y/en": b"<html>moved</html>"})
    with pytest.raises(RuntimeError, match="parsed to 0 recommendations"):
        catalog.sync_listing("Y", empty)
    with pytest.raises(corpus.CorpusMissing, match="itulib catalog sync Y"):
        catalog.load("Y")


def test_details_limit_stops_early(home: Path) -> None:
    second = SERIES_PAGE.replace("Z.11bis", "Z.12").replace("[Withdrawn]", "")
    pages = site(
        {
            f"{catalog.BASE}/rec/T-REC-Z/en": second.encode(),
            f"{catalog.BASE}/rec/T-REC-Z.12/en": RECOMMENDATION_PAGE.encode(),
        }
    )
    fetcher, _ = make_fetcher(home / "cache", Clock(), pages)
    catalog.sync_listing("Z", fetcher)
    assert catalog.sync_details("Z", fetcher, limit=1)[0] == 1
    assert catalog.sync_details("Z", fetcher, limit=1)[0] == 1
    assert catalog.sync_details("Z", fetcher, limit=1)[0] == 0


def test_rows_filter_by_format_text_and_free(home: Path) -> None:
    fetcher, _ = make_fetcher(home / "cache", Clock(), site())
    catalog.sync_listing("Z", fetcher)
    catalog.sync_details("Z", fetcher)
    recs = catalog.load("Z")
    everything = catalog.rows(recs)
    assert [(r.kind, r.label) for r in everything] == [
        ("edition", "Z.10 (01/20)"),
        ("corrigendum", "Z.10 (2020) Corrigendum 1 (01/21)"),
        ("corrigendum", "Z.10 (2020) Corrigendum 2 (07/26)"),
    ], "in force only; the collective file and the superseded components are left out"
    epub = catalog.rows(recs, fmt="EPB")
    assert epub and all("EPB" in r.formats for r in epub)
    assert catalog.rows(recs, fmt="MSW", free_only=True) == [], "Word is TIES-only, so --free excludes it"
    assert catalog.rows(recs, fmt="MSW", free_only=False)
    assert catalog.rows(recs, text="widget") and not catalog.rows(recs, text="zeppelin")
    assert "MSW*" in catalog.rows(recs)[0].formats, "a star marks an asset that is not freely available"
    assert catalog.rows(recs)[0].kind == "edition"


# --- CLI ---------------------------------------------------------------------------------------------------


def test_cli_catalog_list_and_show(home: Path, capsys: pytest.CaptureFixture[str]) -> None:
    fetcher, _ = make_fetcher(home / "cache", Clock(), site())
    catalog.sync_listing("Z", fetcher)
    catalog.sync_details("Z", fetcher)
    assert cli.main(["catalog", "list", "--series", "Z", "--format", "EPB"]) == 0
    out = capsys.readouterr().out
    assert "Z.10" in out and "EPB" in out
    assert "3 of 3 shown" in out, "the edition and its two corrigenda all carry the EPUB in this fixture"
    assert "1 of 2 recommendations" in out, "only Z.10 has details; Z.11bis is withdrawn"
    assert cli.main(["catalog", "show", "Z.10"]) == 0
    shown = capsys.readouterr().out
    assert "superseded" in shown and "corrigendum" in shown and "prepublished" in shown
    assert cli.main(["catalog", "show", "Z.99"]) == 1
    assert cli.main(["catalog", "list", "--series", "Q"]) == 3, "no catalogue yet: error with the remedy, exit 3"
    assert "itulib catalog sync Q" in capsys.readouterr().err


def test_manifest_is_plain_json_under_the_corpus_home(home: Path) -> None:
    fetcher, _ = make_fetcher(home / "cache", Clock(), site())
    catalog.sync_listing("Z", fetcher)
    path = corpus.home() / "catalog" / "series-Z.json"
    assert path.is_file() and json.loads(path.read_text(encoding="utf-8"))["series"] == "Z"
    assert (path.parent.parent).name == "home", "the catalogue lives in ITULIB_HOME, never in the checkout"


def test_reparse_rebuilds_details_from_the_cache_without_requests(home: Path) -> None:
    fetcher, calls = make_fetcher(home / "cache", Clock(), site())
    catalog.sync_listing("Z", fetcher)
    catalog.sync_details("Z", fetcher)
    recs = catalog.load("Z")
    recs["Z.10"]["components"] = [{"stale": True}]
    catalog._save("Z", recs)
    before = len(calls)
    assert catalog.sync_details("Z", fetcher, reparse=True)[0] == 1
    assert len(calls) == before, "reparse reads the cache; it must not touch the network"
    assert catalog.load("Z")["Z.10"]["components"][0].get("id") == "T-REC-Z.10-202001-I"  # type: ignore[index]
