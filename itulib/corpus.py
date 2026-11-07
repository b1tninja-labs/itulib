"""The corpus lives on the user's machine, and this repository never carries it.

What decides the design is the notice printed on page iii of the recommendation itself: ITU reserves all
rights and permits no part of the publication to be reproduced by any means without its prior written
permission. That is quoted here in paraphrase rather than verbatim for the same reason the text is not
vendored, and `tests/test_license.py` fails if a clause sentence ever appears in this tree.

So `fetch` is a command the user runs, the download lands outside the checkout by default, and a clone of this
repository contains code, clause arithmetic and pinned digests - never spec text. The tripwire exists because
the tempting way to make a search test pass is to commit the PDF, and that is the one move a git history
cannot walk back.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import time
import urllib.request

from .sources import Amendment, Edition

Document = Edition | Amendment

DEFAULT_HOME = pathlib.Path.home() / ".itulib"


def home() -> pathlib.Path:
    override = os.environ.get("ITULIB_HOME")
    return pathlib.Path(override) if override else DEFAULT_HOME


def pdf_path(edition: Document) -> pathlib.Path:
    return home() / "corpus" / f"{edition.key.replace('#', '-').replace('!', '-')}.pdf"


def manifest_path() -> pathlib.Path:
    return home() / "manifest.json"


def _record() -> dict[str, dict[str, object]]:
    path = manifest_path()
    if not path.is_file():
        return {}
    loaded = json.loads(path.read_text(encoding="utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def has(edition: Document) -> bool:
    """Present and, if a digest is registered, byte-identical to it."""
    path = pdf_path(edition)
    if not path.is_file():
        return False
    if not edition.sha256:
        return True
    return hashlib.sha256(path.read_bytes()).hexdigest() == edition.sha256


def require(edition: Document) -> pathlib.Path:
    """The local PDF, or an error naming the command that produces it."""
    path = pdf_path(edition)
    if not has(edition):
        raise CorpusMissing(
            f"{edition.key} is not in {home()}.\n"
            f"    Run: itulib fetch {edition.key}   (or: itulib sync)\n"
            f"    The file is copyright ITU and is fetched to your machine rather than shipped with this "
            f"package, so there is no way to obtain it from the repository."
        )
    return path


class CorpusMissing(RuntimeError):
    """The corpus has not been fetched. The remedy is a command, never a committed file."""


def fetch(edition: Document, *, refresh: bool = False) -> pathlib.Path:
    """Download one edition, verify it against the registered digest, and record what arrived."""
    path = pdf_path(edition)
    if has(edition) and not refresh:
        return path
    url = edition.pdf_url
    if url is None:
        raise RuntimeError(f"{edition.key}: no download id is registered, so there is nothing to fetch")
    path.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(url, headers={"User-Agent": "itulib-fetch"})  # noqa: S310
    with urllib.request.urlopen(request, timeout=300) as response:  # noqa: S310
        body = response.read()
    if not body.startswith(b"%PDF"):
        raise RuntimeError(f"{edition.key}: server returned {len(body)} bytes that are not a PDF")
    digest = hashlib.sha256(body).hexdigest()
    if edition.sha256 and digest != edition.sha256:
        raise RuntimeError(
            f"{edition.key}: digest {digest} does not match the registered {edition.sha256}. "
            f"ITU may have re-published the edition; re-verify before trusting any citation from it."
        )
    path.write_bytes(body)
    records = _record()
    records[edition.key] = {
        "sha256": digest,
        "octets": len(body),
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": url,
    }
    manifest_path().write_text(json.dumps(records, indent=2), encoding="utf-8")
    return path
