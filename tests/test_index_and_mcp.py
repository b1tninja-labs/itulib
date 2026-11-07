"""Index staleness and the MCP stdio surface, exercised over invented text.

Nothing here is ITU text: the "pages" are sentences made up for the test, and the "PDF" is a few arbitrary
bytes because the index only hashes the file. That is what lets these run without the corpus, which
`test_license.py` requires of every test.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import anyio
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

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

PAGES = [
    "1.1 Widgets are counted in whole units and never in fractions of a unit.\n"
    "1.2 Gadgets are ordered by colour before they are ordered by size at all.\n"
]


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("ITULIB_HOME", str(tmp_path))
    monkeypatch.setattr(text, "pages", lambda _path: PAGES)
    pdf = corpus.pdf_path(SYNTHETIC)
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"first edition")
    return tmp_path


def test_index_serves_clauses_it_was_built_from(home: Path) -> None:
    assert index.build(SYNTHETIC) == 2
    clause = index.read(SYNTHETIC, "1.2")
    assert clause is not None
    assert "colour" in clause.body
    assert [hit.number for hit in index.search(SYNTHETIC, "widgets")] == ["1.1"]


def test_index_refuses_to_serve_after_the_corpus_changes(home: Path) -> None:
    index.build(SYNTHETIC)
    corpus.pdf_path(SYNTHETIC).write_bytes(b"republished edition")
    with pytest.raises(RuntimeError, match="changed since the index was built"):
        index.search(SYNTHETIC, "widgets")
    with pytest.raises(RuntimeError, match="changed since the index was built"):
        index.read(SYNTHETIC, "1.1")
    index.build(SYNTHETIC)
    assert index.read(SYNTHETIC, "1.1") is not None


def test_a_missing_index_is_an_error_not_an_empty_result(home: Path) -> None:
    with pytest.raises(corpus.CorpusMissing, match="no index"):
        index.search(SYNTHETIC, "widgets")


def test_an_extractor_that_finds_nothing_refuses_to_write_an_index(
    home: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(text, "pages", lambda _path: ["no numbered headings here"])
    with pytest.raises(RuntimeError, match="0 clauses"):
        index.build(SYNTHETIC)


def test_mcp_stdio_handshake_lists_eleven_tools_and_reports_a_missing_corpus(tmp_path: Path) -> None:
    """Drives the real server over stdio. Catches stdout pollution, which importing the module never would."""

    async def drive() -> tuple[set[str], dict[str, object], dict[str, object]]:
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "itulib.mcp"],
            env={**os.environ, "ITULIB_HOME": str(tmp_path)},
            cwd=Path(__file__).resolve().parents[1],
        )
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            names = {tool.name for tool in (await session.list_tools()).tools}
            info = await session.call_tool("itu_info", {})
            search = await session.call_tool("itu_search", {"query": "boolean"})
            return names, _payload(info), _payload(search)

    names, info, search = anyio.run(drive)
    assert names == {
        "itu_info",
        "itu_search",
        "itu_read",
        "itu_outline",
        "itu_grep",
        "itu_errata",
        "itu_cite",
        "itu_links",
        "itu_browse",
        "itu_compare",
        "itu_catalog",
    }
    assert {item["fetched"] for item in info["editions"]} == {False}  # type: ignore[attr-defined]
    assert "error" in search, "a missing corpus must be an error object, never an empty hit list"
    assert "hits" not in search


def _payload(result: object) -> dict[str, object]:
    content = result.content[0]  # type: ignore[attr-defined]
    loaded = json.loads(content.text)
    assert isinstance(loaded, dict)
    return loaded


def test_mcp_without_the_extra_exits_2_with_the_install_hint(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """The first run of a core-only install crashed with a traceback from inside the SDK import, not this."""
    from itulib import cli

    monkeypatch.setitem(sys.modules, "mcp.server.mcpserver", None)
    assert cli.main(["mcp"]) == 2
    assert "itulib[mcp]" in capsys.readouterr().err


def test_tool_results_are_compact_json_with_real_characters() -> None:
    """Indentation and \u00a7 escapes were about a fifth of a typical response, paid for in tokens."""
    from itulib import mcp

    text = mcp._guard({"cite": "Rec. ITU-T X.690 (02/2021) §11.6", "items": [{"n": "1", "t": "x"}], "next": None})
    assert "\n" not in text and ": " not in text and ", " not in text, "no indentation or padding"
    assert "§" in text and "\\u00a7" not in text, "non-ASCII stays as itself, not a six-character escape"
    assert json.loads(text)["cite"].endswith("§11.6"), "still parses to the same value"
