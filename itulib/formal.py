"""ITU-T formal descriptions: a catalogue, a bounded importer, and modules served as documents.

ITU publishes the machine-processable parts of its Recommendations (ASN.1 modules, MIBs, XSD, and others) as
files under `https://www.itu.int/ITU-T/formal-language/`. The web server lists those directories, so the set can
be enumerated without the Recommendation database. What it does not do is serve every listed file: the `.asn`
source is listed but answers 404, and the `.html` rendering beside it is what can be fetched (measured
2026-11-13). The rendering is the source text inside a `<pre>`, one comment line linking to the Recommendation,
and nothing else, so `asn1mod.unwrap_html` recovers it exactly.

Terms: ITU's website terms permit downloading, copying and using content for personal, educational or
non-commercial purposes with the source acknowledged and notices kept, and forbid modification, reproduction,
distribution and derivative works without written permission. They say that publications "may be governed by
specific licensing terms", and no separate licence is stated for this database. So the policy is the one the
rest of this package keeps: **the user fetches, into `ITULIB_HOME`; nothing is vendored, and the only thing
committed is a digest and a size per artifact.** `tests/test_license.py` still applies to this tree.

Nothing here touches the network on its own. Every function that reads a URL takes a `Transport`, so the tests
run offline and a caller can supply a caching or rate-limiting one. `urllib_transport` is the real one.

## Refs

    <Rec>#<year>[-<month>]/<Module>[::<section>]

    X.509#2019-10/AuthenticationFramework                 the module as a document
    X.509#2019-10/AuthenticationFramework::Certificate    one assignment
    X.509#2019/AuthenticationFramework::IMPORTS           a reserved section: IMPORTS, EXPORTS or HEADER

`<Rec>` is the Recommendation as ITU names it (`X.509`, `X.1080.0`; also `G.7712`, `RFC2578` style folders).
`<year>` is the folder the artifact sits in, which is the edition's year. The month is optional because the
folder does not carry it; it is read from the header comment each file opens with, and when a ref gives it
and it disagrees with the file, the ref does not resolve. An edition folder may carry a suffix (`2017-Cor1`),
written after the year: `X.1080.0#2017-Cor1/Module`. A bare `::` section matches an assignment name exactly;
IMPORTS, EXPORTS and HEADER cannot collide with one because they are reserved words in ASN.1.
"""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from . import __version__, asn1mod, corpus

BASE = "https://www.itu.int"
ROOT_PATH = "/ITU-T/formal-language/"
HOST = "www.itu.int"
USER_AGENT = f"itulib-formal/{__version__} (+https://github.com/b1tninja/itulib)"
MIN_INTERVAL = 1.0

MAX_ARTIFACT_OCTETS = 2 * 1024 * 1024
MAX_LISTING_OCTETS = 1024 * 1024
RESERVED_SECTIONS = ("IMPORTS", "EXPORTS", "HEADER")

# Languages by file extension as the listings show them. Only what has been seen is claimed.
LANGUAGES = {".asn": "ASN.1 (listed, not served)", ".html": "ASN.1 or other, rendered as HTML"}

_SEGMENT = re.compile(r"[A-Za-z0-9][A-Za-z0-9._+() -]{0,127}")


class FormalError(RuntimeError):
    """A refusal, with the reason. Never an empty result standing in for one."""


@dataclass(frozen=True)
class Fetched:
    status: int
    body: bytes
    url: str


Transport = Callable[[str, int], Fetched]
"""`(url, max_octets) -> Fetched`. Must not read more than max_octets + 1 and must report the final URL."""


def urllib_transport(url: str, max_octets: int) -> Fetched:
    """The real transport: https to itu.int only, an identifying User-Agent, a bounded read."""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or parts.hostname != HOST:
        raise FormalError(f"refusing {url}: only https://{HOST}/ is fetched")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})  # noqa: S310
    try:
        with urllib.request.urlopen(request, timeout=60) as response:  # noqa: S310
            final = response.geturl()
            body = response.read(max_octets + 1)
            return Fetched(response.status, body, final)
    except urllib.error.HTTPError as error:
        return Fetched(error.code, b"", url)


# --------------------------------------------------------------------------------------------------- pins


@dataclass(frozen=True)
class Pin:
    sha256: str
    octets: int
    month: str = ""  # "10/2019" as the file's header names it


# Digests of the `.html` renderings as served on 2026-11-13. ITU re-renders these files (the x509/2019
# folder carries text from a 2026 corrigendum), so a mismatch means the file changed, not that it was
# tampered with; the remedy is to re-read the change and re-pin, never to skip the check.
PINS: dict[str, Pin] = {
    "itu-t/x/x509/2019/AuthenticationFramework.html": Pin(
        "44a22fa7e191ca9072c479e87388131ac21e727eb1ddaf2c03fc620055f707d2", 21_148, "10/2019"
    ),
    "itu-t/x/x509/2019/CertificateExtensions.html": Pin(
        "b4c921ae4be61043add9aa6b58873dffeebac84ed585e8909779d7a1c5ef97a7", 29_763, "10/2019"
    ),
}


def artifact_url(path: str) -> str:
    return f"{BASE}{ROOT_PATH}{urllib.parse.quote(path)}"


def _check_path(path: str) -> list[str]:
    """Validated segments of a path relative to the formal-language root. Refuses anything odd."""
    segments = path.strip("/").split("/")
    if not path or len(segments) > 8:
        raise FormalError(f"bad artifact path {path!r}")
    for segment in segments:
        if not _SEGMENT.fullmatch(segment) or ".." in segment:
            raise FormalError(f"bad path segment {segment!r} in {path!r}")
    return segments


# ----------------------------------------------------------------------------------------------- listing

_ROW = re.compile(
    r"(?P<date>\d{1,2}/\d{1,2}/\d{4})\s+(?P<time>\d{1,2}:\d{2}\s*[AP]M)\s+"
    r"(?P<size>&lt;dir&gt;|\d+)\s*<A\s+HREF=\"(?P<href>[^\"]{1,512})\">(?P<name>[^<]{1,256})</A>",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Entry:
    name: str
    directory: bool
    size: int
    stamp: str  # as the server prints it: "10/22/2026 7:44 PM"


def parse_listing(page: str, directory: str) -> tuple[list[Entry], int]:
    """Entries of an IIS directory listing, and how many rows were dropped as unsafe.

    `directory` is the path the listing was fetched from, e.g. `/ITU-T/formal-language/itu-t/x/`. A row whose
    link leaves that directory, whose name is not a plain segment, or that repeats is dropped and counted.
    """
    directory = directory if directory.endswith("/") else directory + "/"
    entries: list[Entry] = []
    seen: set[str] = set()
    dropped = 0
    for match in _ROW.finditer(page):
        name = html.unescape(match["name"]).strip()
        href = html.unescape(match["href"])
        is_dir = match["size"].lower() == "&lt;dir&gt;"
        expected = directory + name + ("/" if is_dir else "")
        if urllib.parse.unquote(href) != expected or not _SEGMENT.fullmatch(name) or ".." in name or name in seen:
            dropped += 1
            continue
        seen.add(name)
        entries.append(Entry(name, is_dir, 0 if is_dir else int(match["size"]), f"{match['date']} {match['time']}"))
    return entries, dropped


@dataclass
class Budget:
    """Bounds on one crawl: requests, bytes, depth and entries. Exhaustion is reported, never hidden."""

    max_requests: int = 400
    max_octets: int = 64 * 1024 * 1024
    max_depth: int = 6
    max_entries: int = 20_000
    requests: int = 0
    octets: int = 0
    stopped: str = ""

    def spend(self, octets: int) -> bool:
        self.requests += 1
        self.octets += octets
        if self.requests >= self.max_requests:
            self.stopped = f"request budget {self.max_requests} used"
        elif self.octets >= self.max_octets:
            self.stopped = f"byte budget {self.max_octets} used"
        return not self.stopped


@dataclass(frozen=True)
class Artifact:
    path: str  # relative to the formal-language root: itu-t/x/x509/2019/AuthenticationFramework.html
    size: int
    stamp: str

    @property
    def folder(self) -> str:
        return self.path.rsplit("/", 1)[0]

    @property
    def name(self) -> str:
        return self.path.rsplit("/", 1)[1]


def enumerate_tree(
    transport: Transport,
    start: str = "itu-t/",
    *,
    budget: Budget | None = None,
    pause: Callable[[float], None] = time.sleep,
) -> tuple[list[Artifact], Budget, int]:
    """Walk directory listings below `start`. Returns artifacts, the budget (check `.stopped`) and drops."""
    budget = budget or Budget()
    root = _check_path(start)
    queue: list[tuple[str, int]] = [("/".join(root) + "/", 0)]
    found: list[Artifact] = []
    dropped = 0
    while queue and not budget.stopped:
        relative, depth = queue.pop(0)
        if budget.requests:
            pause(MIN_INTERVAL)
        response = transport(artifact_url(relative), MAX_LISTING_OCTETS)
        budget.spend(len(response.body))
        if response.status != 200 or len(response.body) > MAX_LISTING_OCTETS:
            dropped += 1
            continue
        if urllib.parse.urlsplit(response.url).hostname != HOST:
            raise FormalError(f"listing redirected away from {HOST}: {response.url}")
        entries, bad = parse_listing(response.body.decode("utf-8", errors="replace"), ROOT_PATH + relative)
        dropped += bad
        for entry in entries:
            if entry.directory:
                if depth + 1 <= budget.max_depth:
                    queue.append((relative + entry.name + "/", depth + 1))
            elif len(found) < budget.max_entries:
                found.append(Artifact(relative + entry.name, entry.size, entry.stamp))
    return found, budget, dropped


# ----------------------------------------------------------------------------------------------- storage


def formal_home() -> Path:
    return corpus.home() / "formal"


def artifact_file(path: str) -> Path:
    return formal_home().joinpath("files", *_check_path(path))


def _manifest_file() -> Path:
    return formal_home() / "manifest.json"


def load_manifest() -> dict[str, dict[str, object]]:
    file = _manifest_file()
    if not file.is_file():
        return {}
    loaded = json.loads(file.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def _atomic_write(file: Path, data: bytes) -> None:
    file.parent.mkdir(parents=True, exist_ok=True)
    temporary = file.with_name(f"{file.name}.{os.getpid()}.part")
    temporary.write_bytes(data)
    os.replace(temporary, file)


def _save_manifest(manifest: dict[str, dict[str, object]]) -> None:
    _atomic_write(_manifest_file(), json.dumps(manifest, indent=1, sort_keys=True).encode("utf-8"))


@dataclass(frozen=True)
class Imported:
    path: str
    sha256: str
    octets: int
    pinned: bool
    modules: tuple[str, ...]


def import_artifact(
    path: str,
    transport: Transport,
    *,
    trust_first_use: bool = False,
    pins: dict[str, Pin] | None = None,
) -> Imported:
    """Fetch one artifact into ITULIB_HOME, verified, parsed, and recorded.

    A pinned artifact must hash to its pin. An unpinned one is refused unless the caller says
    `trust_first_use`, in which case it is stored marked unpinned with its digest reported so it can be pinned.
    Nothing is written until the bytes have been size-checked, hashed and parsed.
    """
    pins = PINS if pins is None else pins
    _check_path(path)
    if not path.endswith(".html"):
        raise FormalError(f"{path}: only the .html rendering is served by ITU (the .asn listing entry is a 404)")
    pin = pins.get(path)
    if pin is None and not trust_first_use:
        raise FormalError(f"{path} has no pinned digest. Re-run with trust_first_use to store it unpinned.")
    response = transport(artifact_url(path), MAX_ARTIFACT_OCTETS)
    if urllib.parse.urlsplit(response.url).hostname != HOST:
        raise FormalError(f"{path}: redirected away from {HOST} to {response.url}")
    if response.status != 200:
        raise FormalError(f"{path}: HTTP {response.status}")
    body = response.body
    if len(body) > MAX_ARTIFACT_OCTETS:
        raise FormalError(f"{path}: larger than the {MAX_ARTIFACT_OCTETS} octet bound")
    digest = hashlib.sha256(body).hexdigest()
    if pin is not None and (digest != pin.sha256 or len(body) != pin.octets):
        raise FormalError(
            f"{path}: digest {digest} ({len(body)} octets) does not match the pinned "
            f"{pin.sha256} ({pin.octets}). ITU re-renders these files; read the change before re-pinning."
        )
    try:
        text, note = asn1mod.unwrap_html(body)
        modules = asn1mod.parse_modules(text)
    except asn1mod.ModuleError as error:
        raise FormalError(f"{path}: not readable as ASN.1: {error}") from error
    _atomic_write(artifact_file(path), body)
    manifest = load_manifest()
    manifest[path] = {
        "sha256": digest,
        "octets": len(body),
        "pinned": pin is not None,
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": artifact_url(path),
        "header_edition": note,
        "modules": [module.name for module in modules],
        "form": (
            "Asnp-rendered HTML, markup stripped"
            if b"Generated by Asnp" in body
            else "source text in <pre>, wrapper stripped"
        ),
    }
    _save_manifest(manifest)
    return Imported(path, digest, len(body), pin is not None, tuple(m.name for m in modules))


def save_catalogue(artifacts: list[Artifact]) -> Path:
    """Record an enumeration (paths, sizes, listing dates) beside the files. Metadata only."""
    file = formal_home() / "catalogue.json"
    rows = [asdict(a) for a in sorted(artifacts, key=lambda a: a.path)]
    _atomic_write(
        file,
        json.dumps(
            {"enumerated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "artifacts": rows}, indent=0
        ).encode("utf-8"),
    )
    return file


# ------------------------------------------------------------------------------------------------- refs


@dataclass(frozen=True)
class FormalRef:
    rec: str
    year: str
    month: str | None
    suffix: str
    module: str
    section: str | None

    @property
    def edition(self) -> str:
        return self.year + (f"-{self.month}" if self.month else "") + (f"-{self.suffix}" if self.suffix else "")


_REF = re.compile(
    r"(?P<rec>[A-Za-z]{1,6}\.?[0-9][A-Za-z0-9.]{0,15})#(?P<year>\d{4})(?:-(?P<month>(?:0[1-9]|1[0-2])))?"
    r"(?:-(?P<suffix>[A-Za-z][A-Za-z0-9]{0,15}))?/(?P<module>[A-Za-z][A-Za-z0-9-]{0,127})"
    r"(?:::(?P<section>[A-Za-z][A-Za-z0-9-]{0,127}))?"
)


def parse_formal_ref(ref: str) -> FormalRef:
    match = _REF.fullmatch(ref.strip())
    if not match:
        raise FormalError(f"{ref!r} is not a formal-description ref: expected Rec#year[-mm]/Module[::section]")
    return FormalRef(
        match["rec"], match["year"], match["month"], match["suffix"] or "", match["module"], match["section"]
    )


def _folder_matches(folder: str, ref: FormalRef) -> bool:
    parts = folder.split("/")
    rec_folder = ref.rec.lower().replace(".", "")
    edition_folder = ref.year + (f"-{ref.suffix}" if ref.suffix else "")
    return len(parts) >= 2 and parts[-2].lower().replace(".", "") == rec_folder and parts[-1] == edition_folder


def _month_year(note: str | None) -> tuple[str, str] | None:
    found = re.search(r"\((\d{2})/(\d{4})\)", note or "")
    return (found.group(2), found.group(1)) if found else None


def resolve(ref: FormalRef, manifest: dict[str, dict[str, object]] | None = None) -> str:
    """The artifact path a ref names among the imported ones, or a refusal that says why."""
    manifest = load_manifest() if manifest is None else manifest
    candidates = [
        path
        for path, info in manifest.items()
        if path.endswith(".html")
        and _folder_matches(path.rsplit("/", 1)[0], ref)
        and ref.module in info.get("modules", [])  # type: ignore[operator]
    ]
    if not candidates:
        raise FormalError(
            f"{ref.rec}#{ref.edition}/{ref.module} is not imported. Import it with "
            f"`python -m itulib.formal import <path>`; list what is imported with `python -m itulib.formal list`."
        )
    if len(candidates) > 1:
        raise FormalError(f"ambiguous: {sorted(candidates)}")
    path = candidates[0]
    stated = _month_year(str(manifest[path].get("header_edition")))
    if ref.month and stated and (stated[0], stated[1]) != (ref.year, ref.month):
        raise FormalError(
            f"{path} states edition {stated[1]}/{stated[0]}, not {ref.month}/{ref.year}; "
            f"the ref does not resolve rather than citing a different edition"
        )
    return path


# ------------------------------------------------------------------------------------------- documents


def read(ref_text: str, manifest: dict[str, dict[str, object]] | None = None) -> dict[str, object]:
    """Serve a ref as a document: the module as a whole, or one section of it."""
    ref = parse_formal_ref(ref_text)
    manifest = load_manifest() if manifest is None else manifest
    path = resolve(ref, manifest)
    info = manifest[path]
    text, _ = asn1mod.unwrap_html(artifact_file(path).read_bytes())
    if hashlib.sha256(artifact_file(path).read_bytes()).hexdigest() != info["sha256"]:
        raise FormalError(f"{path}: stored bytes no longer match the recorded digest; re-import")
    modules = {m.name: m for m in asn1mod.parse_modules(text)}
    module = modules.get(ref.module)
    if module is None:
        raise FormalError(f"{path} has no module {ref.module}")
    stated = str(info.get("header_edition") or "") or None
    cite = (
        f"ITU-T {stated} formal description, module {module.name}"
        if stated
        else f"ITU-T {ref.rec} ({ref.year}) formal description, module {module.name}"
    )
    result: dict[str, object] = {
        "ref": ref_text.strip(),
        "module": module.name,
        "oid": module.oid,
        "oid_text": module.oid_text,
        "source": info.get("source"),
        "sha256": info["sha256"],
        "pinned": info.get("pinned"),
        "form": info.get("form"),
        "cite": cite,
    }
    section = ref.section
    if section is None:
        result.update(
            tagging=module.tagging,
            extensibility_implied=module.extensibility_implied,
            exports=module.exports
            if module.exports is None or isinstance(module.exports, str)
            else list(module.exports),
            imports=[
                {"module": i.module, "oid_text": i.oid_text, "symbols": list(i.symbols)} for i in module.imports
            ],
            sections=[{"name": a.name, "kind": a.kind, "line": a.line} for a in module.assignments],
        )
        return result
    if section == "IMPORTS":
        result["imports"] = [
            {"module": i.module, "oid_text": i.oid_text, "symbols": list(i.symbols)} for i in module.imports
        ]
        return result
    if section == "EXPORTS":
        result["exports"] = (
            module.exports if module.exports is None or isinstance(module.exports, str) else list(module.exports)
        )
        return result
    if section == "HEADER":
        result["text"] = text[: text.find("BEGIN") + 5] if "BEGIN" in text else ""
        return result
    found = module.assignment(section)
    if found is None:
        raise FormalError(f"{module.name} has no assignment {section}")
    result.update(
        name=found.name, kind=found.kind, parameterised=found.parameterised, line=found.line, text=found.text
    )
    return result


def listing() -> list[dict[str, object]]:
    return [
        {
            "path": p,
            **{k: v for k, v in i.items() if k in {"sha256", "octets", "pinned", "modules", "header_edition"}},
        }
        for p, i in sorted(load_manifest().items())
    ]


def main(argv: list[str] | None = None) -> int:
    import argparse
    import sys

    parser = argparse.ArgumentParser(prog="python -m itulib.formal", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    enum = sub.add_parser("enumerate", help="walk the directory listings and record the catalogue")
    enum.add_argument("start", nargs="?", default="itu-t/x/")
    enum.add_argument("--max-requests", type=int, default=400)
    imp = sub.add_parser("import", help="fetch artifacts (the .html path under formal-language/) into ITULIB_HOME")
    imp.add_argument("paths", nargs="+")
    imp.add_argument("--trust-first-use", action="store_true")
    sub.add_parser("list", help="what is imported")
    rd = sub.add_parser("read", help="serve a ref: Rec#year[-mm]/Module[::section]")
    rd.add_argument("ref")
    args = parser.parse_args(argv)
    try:
        if args.command == "enumerate":
            artifacts, budget, dropped = enumerate_tree(
                urllib_transport, args.start, budget=Budget(max_requests=args.max_requests)
            )
            file = save_catalogue(artifacts)
            print(
                json.dumps(
                    {
                        "artifacts": len(artifacts),
                        "requests": budget.requests,
                        "stopped": budget.stopped,
                        "dropped": dropped,
                        "catalogue": str(file),
                    }
                )
            )
        elif args.command == "import":
            for path in args.paths:
                done = import_artifact(path, urllib_transport, trust_first_use=args.trust_first_use)
                print(json.dumps(asdict(done)))
                time.sleep(MIN_INTERVAL)
        elif args.command == "list":
            print(json.dumps(listing(), indent=1))
        else:
            print(json.dumps(read(args.ref), indent=1))
    except FormalError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
