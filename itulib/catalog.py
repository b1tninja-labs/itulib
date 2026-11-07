"""The ITU-T catalogue: which recommendations exist, which editions are in force, and in which formats.

ITU publishes no bulk download and no machine-readable index of recommendations, so this reads the same public
HTML pages a person would, politely: one request per second, an identifying User-Agent, a disk cache, and only
paths that robots.txt does not disallow (`/rec/`). Three page types matter:

- the **series listing** (`/rec/T-REC-X/en`): every recommendation number with its title and, for withdrawn
  ones, a `[Withdrawn]` marker;
- the **recommendation page** (`/rec/T-REC-X.509/en`): its components, in two sections ("In force components",
  "Superseded and Withdrawn components"), each an edition, corrigendum, amendment, erratum or collective file;
- the **component page** (`/rec/T-REC-X.509-201910-I/en`): the assets of one component, each with a format,
  language, size, posting date and an access class (freely available, or TIES users only).

Only metadata is kept: numbers, titles, statuses, sizes, dates and URLs. No recommendation text, and nothing is
written into the repository: everything lives under `ITULIB_HOME/catalog/`. The parsers are pure functions of
HTML so they are tested on invented pages; the shapes they expect were read from live pages on 2026-11-07, and a
page that no longer matches yields an empty result that `sync` reports, never a silent partial catalogue.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass, field
from pathlib import Path

from . import __version__, corpus

BASE = "https://www.itu.int"
USER_AGENT = f"itulib-catalog/{__version__} (+https://github.com/b1tninja/itulib)"
MIN_INTERVAL = 1.0

# Asset format ids as they appear in download links, with what they are.
FORMATS = {
    "PDF": "PDF (acrobat)",
    "EPB": "EPUB",
    "MSW": "Word 2007",
    "ZWD": "zip of Word files",
    "SUM-HTM": "summary (HTML)",
    "TOC-HTM": "table of contents (HTML)",
}


@dataclass(frozen=True)
class Listing:
    rec: str  # "X.509"
    title: str
    status: str  # "active" | "withdrawn" | other marker, lowercased
    note: str = ""


@dataclass(frozen=True)
class Component:
    id: str  # "T-REC-X.509-201910-I", "T-REC-X.509-200003-S!Cor1"
    label: str  # "X.509 (10/19)"
    kind: str  # edition | corrigendum | amendment | erratum | supplement | collection | other
    status: str  # "in force" | "superseded" | "withdrawn" | as printed, lowercased
    section: str  # "in force" | "superseded"
    title: str = ""


@dataclass(frozen=True)
class Asset:
    fmt: str  # "PDF", "EPB", "MSW", "ZWD", "SUM-HTM", "TOC-HTM"
    lang: str  # "E", "F", "S", ...
    url: str
    size: int | None  # octets, when the page prints one
    posted: str  # ISO date, or ""
    access: str  # "free" | "ties" | "unknown"


@dataclass(frozen=True)
class ComponentPage:
    id: str
    title: str
    status: str
    approved: str
    assets: tuple[Asset, ...] = field(default_factory=tuple)


# --- parsing ------------------------------------------------------------------------------------------------

_TAG = re.compile(r"<[^>]+>")
_SPACE = re.compile(r"\s+")
_ROW = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.S | re.I)
_CELLS = re.compile(r"<td\b[^>]*>(.*?)</td>", re.S | re.I)
_REC_LINK = re.compile(r'href="\./recommendation\.asp\?lang=en&amp;parent=(T-REC-[^"&]+)"', re.I)
_COMPONENT = re.compile(r"^T-REC-([A-Z]\.[\w]+(?:-[A-Z]\.[\w]+)?)-(\d{6})-([A-Z])(?:!(.+))?$")
_DOWNLOAD = re.compile(r'href="([^"]*dologin_pub\.asp\?[^"]*?id=([^"&]+)[^"]*)"', re.I)
_STATIC = re.compile(r'href="(/dms_pubrec/[^"]+!!(SUM-HTM|TOC-HTM)-([A-Z])\.htm)"', re.I)


def text_of(fragment: str) -> str:
    cleaned = html.unescape(_TAG.sub(" ", fragment)).replace("�", " ").replace("\xa0", " ")
    return _SPACE.sub(" ", cleaned).strip()


def decode(body: bytes) -> str:
    """ITU's pages are a mix of UTF-8 and cp1252. Try the strict one first so the fallback is never silent."""
    try:
        return body.decode("utf-8")
    except UnicodeDecodeError:
        return body.decode("cp1252", errors="replace")


def parse_series(page: str) -> list[Listing]:
    """One entry per recommendation number on a series listing page."""
    found: list[Listing] = []
    for row in _ROW.findall(page):
        link = _REC_LINK.search(row)
        cells = _CELLS.findall(row)
        if not link or len(cells) < 2 or _COMPONENT.match(link.group(1)):  # no link, or a component row
            continue
        ident = link.group(1).removeprefix("T-REC-")
        rendered = text_of(cells[1])
        marker = re.match(r"\[([^\]]+)\]\s*", rendered)
        status = marker.group(1).lower() if marker else "active"
        rendered = rendered[marker.end() :] if marker else rendered
        note = ""
        if "<br" in cells[1].lower():
            head, _, tail = cells[1].partition("<br")
            rendered = text_of(head).removeprefix(marker.group(0)) if marker else text_of(head)
            note = text_of("<br" + tail)
        found.append(Listing(rec=ident, title=rendered, status=status, note=note))
    return found


def _kind(suffix: str | None, collection: bool) -> str:
    if collection:
        return "collection"
    if not suffix:
        return "edition"
    lowered = suffix.lower()
    for word, kind in (("cor", "corrigendum"), ("amd", "amendment"), ("err", "erratum"), ("sup", "supplement")):
        if lowered.startswith(word):
            return kind
    return "other"


def parse_recommendation(page: str) -> list[Component]:
    """The components listed on a recommendation page, with the section each one sits under."""
    out: list[Component] = []
    section = "in force"
    for row in _ROW.findall(page):
        header = text_of(row).lower()
        if 'colspan="3"' in row.lower() or "colspan='3'" in row.lower():
            section = "superseded" if "superseded" in header or "withdrawn" in header else "in force"
            continue
        link = _REC_LINK.search(row)
        cells = _CELLS.findall(row)
        if not link or len(cells) < 3:
            continue
        match = _COMPONENT.match(link.group(1))
        if not match:
            continue
        status = text_of(cells[2]).lower()
        out.append(
            Component(
                id=link.group(1),
                label=text_of(cells[0]),
                kind=_kind(match.group(4), "-" in match.group(1)),
                status=status,
                section=section,
                title=text_of(cells[1]),
            )
        )
    return out


def _size(near: str) -> int | None:
    m = re.search(r"(\d[\d,]*)\s*bytes", near)
    return int(m.group(1).replace(",", "")) if m else None


def parse_component(page: str, component_id: str) -> ComponentPage:
    """Title, status, approval date and every downloadable asset of one component page."""
    plain = text_of(re.sub(r"<script.*?</script>|<style.*?</style>", " ", page, flags=re.S | re.I))
    status = re.search(r"Status\s*:\s*([A-Za-z ]+?)(?:\s{2,}|\s+(?:Table|Summary|Access)\b|$)", plain)
    approved = re.search(r"Approved in\s*(\d{4}-\d{2}-\d{2})", plain)
    title = re.search(r"<title>(.*?)</title>", page, re.S | re.I)
    # Access labels in document order ("Access : Freely available items", "Access : TIES users"). The label's
    # words can sit outside the tag that holds "Access :", so classify the text that follows it, not the tag.
    labels = [
        (m.start(), _access_class(text_of(page[m.end() : m.end() + 240])[:40]))
        for m in re.finditer(r"Access\s*:", page)
    ]
    assets: list[Asset] = []
    for m in _DOWNLOAD.finditer(page):
        # editions use "!!PDF-E", corrigenda/amendments/errata a single "!" ("...!Err1!PDF-E")
        parsed = re.search(r"!([A-Z]+(?:-[A-Z]+)?)-([A-Z])$", m.group(2))
        if not parsed:
            continue
        # The size and posting date are cells of the same table row as the download link, before it in some
        # tables and after it in others, so read the whole enclosing row.
        stop = page.find("</tr>", m.end())
        row = text_of(page[max(page.rfind("<tr", 0, m.start()), 0) : stop if stop > 0 else m.end()])
        date = re.search(r"(\d{4}-\d{2}-\d{2})", row)
        before = [kind for pos, kind in labels if pos < m.start()]
        assets.append(
            Asset(
                fmt=parsed.group(1),
                lang=parsed.group(2),
                url=_absolute(html.unescape(m.group(1)).strip()),
                size=_size(row),
                posted=date.group(1) if date else "",
                access=before[-1] if before else "unknown",
            )
        )
    for m in _STATIC.finditer(page):
        assets.append(Asset(m.group(2), m.group(3), _absolute(m.group(1)), None, "", "free"))
    unique = {(a.fmt, a.lang, a.url): a for a in assets}
    return ComponentPage(
        id=component_id,
        title=text_of(title.group(1)) if title else "",
        status=status.group(1).strip().lower() if status else "",
        approved=approved.group(1) if approved else "",
        assets=tuple(unique.values()),
    )


def _access_class(label: str) -> str:
    lowered = label.lower()
    if "free" in lowered:
        return "free"
    if "ties" in lowered:
        return "ties"
    return "unknown"


def _absolute(href: str) -> str:
    return href if href.startswith("http") else BASE + (href if href.startswith("/") else "/rec/" + href)


# --- fetching -----------------------------------------------------------------------------------------------


class Fetcher:
    """GET with a minimum interval between requests, an identifying User-Agent and a disk cache.

    `opener` and the clock are injectable so the pacing and the cache are tested without a network.
    """

    def __init__(
        self,
        cache: Path | None = None,
        *,
        interval: float = MIN_INTERVAL,
        opener: Callable[[urllib.request.Request], bytes] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.cache = cache
        self.interval = interval
        self._opener = opener or self._open
        self._sleep = sleep
        self._clock = clock
        self._last = float("-inf")
        self.requests = 0

    @staticmethod
    def _open(request: urllib.request.Request) -> bytes:
        with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
            return bytes(response.read())

    def get(self, url: str, *, refresh: bool = False) -> str:
        if not url.startswith(BASE + "/rec/") and not url.startswith(BASE + "/dms_pubrec/"):
            raise ValueError(f"refusing to fetch {url}: the catalogue reads only /rec/ and /dms_pubrec/")
        slot = self.cache / (hashlib.sha256(url.encode()).hexdigest()[:24] + ".html") if self.cache else None
        if slot is not None and slot.is_file() and not refresh:
            return decode(slot.read_bytes())
        wait = self.interval - (self._clock() - self._last)
        if wait > 0:
            self._sleep(wait)
        self._last = self._clock()
        self.requests += 1
        body = self._opener(urllib.request.Request(url, headers={"User-Agent": USER_AGENT}))  # noqa: S310
        if slot is not None:
            slot.parent.mkdir(parents=True, exist_ok=True)
            slot.write_bytes(body)
        return decode(body)


# --- manifest -----------------------------------------------------------------------------------------------


def catalog_dir() -> Path:
    return corpus.home() / "catalog"


def _manifest(series: str) -> Path:
    return catalog_dir() / f"series-{series}.json"


def series_url(letter: str) -> str:
    return f"{BASE}/rec/T-REC-{letter}/en"


def load(series: str) -> dict[str, dict[str, object]]:
    path = _manifest(series)
    if not path.is_file():
        raise corpus.CorpusMissing(f"no catalogue for series {series}. Run: itulib catalog sync {series}")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    recs = loaded.get("recs", {}) if isinstance(loaded, dict) else {}
    return recs if isinstance(recs, dict) else {}


def _save(series: str, recs: dict[str, dict[str, object]]) -> None:
    path = _manifest(series)
    path.parent.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    path.write_text(json.dumps({"series": series, "updated": stamp, "recs": recs}, indent=1), encoding="utf-8")


def sync_listing(letter: str, fetcher: Fetcher, *, refresh: bool = False) -> int:
    """Read the series listing and merge it into the manifest, keeping any details already fetched."""
    listings = parse_series(fetcher.get(series_url(letter), refresh=refresh))
    if not listings:
        raise RuntimeError(
            f"series {letter}: the listing page parsed to 0 recommendations. The page layout probably changed; "
            f"refusing to write an empty catalogue."
        )
    try:
        recs = load(letter)
    except corpus.CorpusMissing:
        recs = {}
    for item in listings:
        entry = recs.setdefault(item.rec, {})
        entry.update(asdict(item))
    _save(letter, recs)
    return len(listings)


def sync_details(
    letter: str,
    fetcher: Fetcher,
    *,
    limit: int | None = None,
    include_withdrawn: bool = False,
    refresh: bool = False,
    reparse: bool = False,
    only: Iterable[str] | None = None,
    progress: Callable[[str], None] = lambda _message: None,
) -> tuple[int, int]:
    """Fetch the components, and the assets of the in-force ones, for recommendations without details yet.

    Resumable: a recommendation with details is skipped unless `refresh` (also ignore the page cache) or
    `reparse` (redo the details from the cached pages, with no requests: for after a parser change). The
    manifest is saved after each one, so an interrupted run loses nothing. Returns (recommendations done,
    component pages read).
    """
    recs = load(letter)
    wanted = set(only) if only is not None else None
    done = pages = 0
    for rec, entry in list(recs.items()):
        if wanted is not None and rec not in wanted:
            continue
        if entry.get("status") != "active" and not include_withdrawn:
            continue
        if entry.get("components") is not None and not (refresh or reparse):
            continue
        if limit is not None and done >= limit:
            break
        components = parse_recommendation(fetcher.get(f"{BASE}/rec/T-REC-{rec}/en", refresh=refresh))
        details: list[dict[str, object]] = []
        for component in components:
            record: dict[str, object] = asdict(component)
            if component.section == "in force" and component.kind != "collection":
                page = parse_component(fetcher.get(f"{BASE}/rec/{component.id}/en", refresh=refresh), component.id)
                pages += 1
                record.update(approved=page.approved, assets=[asdict(a) for a in page.assets])
            details.append(record)
        entry["components"] = details
        _save(letter, recs)
        done += 1
        progress(f"{rec}: {len(components)} components")
    return done, pages


def flatten(recs: dict[str, dict[str, object]]) -> Iterable[tuple[str, dict[str, object], dict[str, object]]]:
    """(rec, recommendation entry, component) for every component that has details."""
    for rec, entry in recs.items():
        components = entry.get("components")
        if isinstance(components, list):
            for component in components:
                if isinstance(component, dict):
                    yield rec, entry, component


def assets_of(component: dict[str, object]) -> list[dict[str, object]]:
    """The asset records of a component, or [] when its assets were not fetched."""
    raw = component.get("assets")
    return [a for a in raw if isinstance(a, dict)] if isinstance(raw, list) else []


def best_source(component: dict[str, object]) -> dict[str, object]:
    """Which assets to use for one in-force component, in order of how much structure they carry.

    EPUB carries the document's own structure but is rare; the PDF is nearly always there and free; the static
    table-of-contents page is an independent check on the PDF's bookmarks. Word is never preferred: it is
    TIES-only for most documents.
    """
    assets = assets_of(component)
    free = [a for a in assets if a.get("access") == "free" and a.get("lang") == "E"]
    by_fmt = {str(a["fmt"]): a for a in free}
    return {
        "primary": by_fmt.get("EPB") or by_fmt.get("PDF"),
        "pdf": by_fmt.get("PDF"),
        "epub": by_fmt.get("EPB"),
        "toc": by_fmt.get("TOC-HTM"),
        "summary": by_fmt.get("SUM-HTM"),
    }


@dataclass(frozen=True)
class Row:
    rec: str
    title: str
    component: str
    label: str
    kind: str  # edition | corrigendum | amendment | erratum | supplement | other
    approved: str
    formats: tuple[str, ...]  # format ids; a trailing * marks one that is not freely available

    def summary(self) -> str:
        return " ".join(self.formats)


def rows(
    recs: dict[str, dict[str, object]],
    *,
    text: str = "",
    fmt: str = "",
    status: str = "in force",
    free_only: bool = False,
) -> list[Row]:
    """One row per in-force component with details (editions, and their corrigenda, amendments and errata)."""
    wanted = text.lower()
    found: list[Row] = []
    for rec, entry, component in flatten(recs):
        # Collective files ("X.680-X.693") are Word archives of several recommendations, not a document of this one.
        if component.get("section") != "in force" or component.get("kind") == "collection":
            continue
        if status and not str(component.get("status", "")).startswith(status):
            continue
        assets = assets_of(component)
        if fmt and not any(a.get("fmt") == fmt and (a.get("access") == "free" or not free_only) for a in assets):
            continue
        haystack = f"{rec} {entry.get('title', '')} {component.get('label', '')}".lower()
        if wanted and wanted not in haystack:
            continue
        found.append(
            Row(
                rec=rec,
                title=str(entry.get("title", "")),
                component=str(component["id"]),
                label=str(component.get("label", "")),
                kind=str(component.get("kind", "")),
                approved=str(component.get("approved", "")),
                formats=tuple(sorted({f"{a['fmt']}{'' if a.get('access') == 'free' else '*'}" for a in assets})),
            )
        )
    return found
