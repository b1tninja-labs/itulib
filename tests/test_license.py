"""The repository must contain no ITU text. This test exists because the shortcut is so tempting.

The easy way to make a search test pass is to commit the PDF, and once it is in history the only repair is a
rewrite. ITU's notice on page iii of X.690 (02/2021) reserves all rights and forbids reproduction by any means
without written permission, so the corpus is fetched by the user into ITULIB_HOME and never tracked.

These are tripwires, not proofs: they catch a committed PDF, a vendored extract, and a verbatim clause pasted
into a docstring or a fixture. They cannot catch every possible copy, and the honest statement of that limit
is here rather than in a claim of completeness.
"""

from __future__ import annotations

import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]

# Sentences that appear in the real recommendation and would be reproduction if they appeared here.
FORBIDDEN_PHRASES = (
    "shall appear in ascending order",
    "all eight bits set to one",
    "smallest possible number of octets",
    "bits 7 to 1 of the first subsequent octet shall not all be zero",
    "No part of this publication may be reproduced",
)

BINARY_SUFFIXES = {".pdf", ".doc", ".docx", ".zip", ".epub", ".pdb"}


def _sources() -> list[pathlib.Path]:
    skip = {".git", ".venv", "__pycache__", "corpus", ".ruff_cache", ".mypy_cache", ".pytest_cache"}
    return [path for path in ROOT.rglob("*") if path.is_file() and not any(part in skip for part in path.parts)]


def _scan() -> list[pathlib.Path]:
    """Everything except this file.

    The guard cannot apply to itself: naming the sentences it forbids is how it forbids them, and rewriting
    them as concatenations of fragments would only hide the same text from a human reader while making the
    check look stricter than it is. Excluding the file is the honest version of that trade, and the exclusion
    is asserted rather than assumed by test_the_guard_file_is_the_only_exception.
    """
    return [path for path in _sources() if path.name != "test_license.py"]


def test_no_specification_binaries_anywhere_in_the_tree() -> None:
    offenders = [str(path.relative_to(ROOT)) for path in _sources() if path.suffix.lower() in BINARY_SUFFIXES]
    assert not offenders, f"ITU text may not be vendored: {offenders}"


def test_the_guard_file_is_the_only_exception() -> None:
    scan = {path.name for path in _scan()}
    assert "test_license.py" not in scan
    assert "test_text.py" in scan, "the exclusion must be a single named file, not a directory"


def test_no_verbatim_clause_text_in_source() -> None:
    for path in _scan():
        if path.suffix not in {".py", ".md", ".toml", ".txt"}:
            continue
        body = path.read_text(encoding="utf-8", errors="replace")
        for phrase in FORBIDDEN_PHRASES:
            assert phrase not in body, f"{path.relative_to(ROOT)} quotes specification text: {phrase!r}"


def test_the_corpus_directory_is_ignored() -> None:
    ignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "corpus/" in ignore, "the fetch target must be ignored, or a git add -A commits the corpus"


def test_no_test_requires_the_corpus() -> None:
    """A test that needs the PDF cannot run in CI, and a suite that skips quietly reports green."""
    for path in (ROOT / "tests").glob("*.py"):
        if path.name == "test_license.py":
            continue
        assert "corpus.require" not in path.read_text(encoding="utf-8"), path.name
