"""Formal descriptions: the ASN.1 module reader, the listing parser, and the importer behind a fake transport.

Every module and listing here is invented. Names, OIDs and rules are made up, so `tests/test_license.py` has
nothing to object to and no network is touched. The real files were checked by hand against the same parsers
(see ROADMAP `ia.formal_import`): that check cannot be a test.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from itulib import asn1mod, formal

MODULE = """-- invented module for tests
Widgets-Core
  {joint-iso-itu-t example(99) module(1) widgetsCore(7) 3}
DEFINITIONS IMPLICIT TAGS ::=
BEGIN

-- EXPORTS All
IMPORTS
  id-w, Gadget{}, Knob
    FROM Widgets-Base
      {joint-iso-itu-t example(99) module(1) widgetsBase(1) 3} WITH SUCCESSORS
  Dial FROM Widgets-Dials;

/* a block comment
   with ::= inside it, which must not start an assignment
*/
Widget ::= SEQUENCE {
  serial    INTEGER (0..MAX),   -- trailing ::= in a comment
  label     UTF8String OPTIONAL,
  ...,
  [[2: extra BOOLEAN DEFAULT TRUE]]
}

id-widget  OBJECT IDENTIFIER ::= {id-w 4}

WIDGET-CLASS ::= CLASS {
  &id   OBJECT IDENTIFIER UNIQUE,
  &Type
} WITH SYNTAX {ID &id TYPE &Type}

Pair{T, U} ::= SEQUENCE { first T, second U }

SupportedWidgets WIDGET-CLASS ::= { ... }

Greeting ::= UTF8String ("a ::= b" | "say ""hi"" ")

END -- Widgets-Core
"""


def wrap(text: str) -> bytes:
    body = text.replace("&", "&amp;").replace("\n", "\r\n")
    head = "<html><head><title>x</title></head><body><pre>"
    link = '<i>-- ASN module extracted from <a href="https://www.itu.int/x">ITU-T X.999 (03/2031)</a></i><br><br>'
    return f"{head}{link}{body}</pre></body></html>".encode()


def parsed() -> asn1mod.Module:
    return asn1mod.parse_modules(MODULE)[0]


def test_module_header_oid_and_tagging() -> None:
    module = parsed()
    assert module.name == "Widgets-Core"
    assert module.oid == "2.99.1.7.3"
    assert module.tagging == "IMPLICIT"
    assert module.exports is None  # the EXPORTS line is a comment, so there is no clause


def test_imports_keep_oids_successors_and_parameterised_symbols() -> None:
    first, second = parsed().imports
    assert first.module == "Widgets-Base"
    assert first.symbols == ("id-w", "Gadget{}", "Knob")
    assert first.with_successors and first.oid_text and "widgetsBase(1)" in first.oid_text
    assert (second.module, second.symbols, second.oid_text) == ("Widgets-Dials", ("Dial",), None)


def test_assignments_are_split_at_real_assignment_operators_only() -> None:
    kinds = {a.name: a.kind for a in parsed().assignments}
    assert kinds == {
        "Widget": "type",
        "id-widget": "value",
        "WIDGET-CLASS": "class",
        "Pair": "type",
        "SupportedWidgets": "set",
        "Greeting": "type",
    }
    assert parsed().assignment("Pair").parameterised  # type: ignore[union-attr]
    assert "Widget ::=" in parsed().assignment("Widget").text  # type: ignore[union-attr]
    assert "extra BOOLEAN" in parsed().assignment("Widget").text  # type: ignore[union-attr]
    assert parsed().assignment("Greeting").text.endswith('"say ""hi"" ")')  # type: ignore[union-attr]


def test_html_wrapper_is_removed_and_the_edition_comes_from_the_header() -> None:
    text, note = asn1mod.unwrap_html(wrap(MODULE))
    assert note == "X.999 (03/2031)"
    assert "<pre>" not in text and "\r" not in text
    assert asn1mod.parse_modules(text)[0].name == "Widgets-Core"


def test_exports_all_and_lists() -> None:
    explicit = asn1mod.parse_modules("M DEFINITIONS ::= BEGIN EXPORTS All; A ::= INTEGER END")[0]
    listed = asn1mod.parse_modules("M DEFINITIONS ::= BEGIN EXPORTS A, b; A ::= INTEGER\nb A ::= 1 END")[0]
    assert explicit.exports == "all" and listed.exports == ("A", "b")


def test_two_modules_in_one_file() -> None:
    modules = asn1mod.parse_modules(
        "A DEFINITIONS ::= BEGIN X ::= INTEGER END\nB DEFINITIONS ::= BEGIN Y ::= NULL END"
    )
    assert [m.name for m in modules] == ["A", "B"]


@pytest.mark.parametrize(
    "hostile",
    [
        "",
        "no module here at all",
        "M DEFINITIONS ::= BEGIN A ::= INTEGER",  # no END
        "M DEFINITIONS ::= BEGIN /* never closed A ::= INTEGER END",
        'M DEFINITIONS ::= BEGIN A ::= "never closed END',
        "M DEFINITIONS ::= BEGIN IMPORTS A FROM END",
        "M DEFINITIONS ::= BEGIN IMPORTS A FROM B END",  # no ';'
        "M DEFINITIONS ::= BEGIN A ::= " + "{" * 500 + " END",
        "M DEFINITIONS WEIRD ::= BEGIN END",
        "M DEFINITIONS ::= BEGIN A ::= INTEGER\x00 END",
    ],
)
def test_hostile_text_is_an_error_not_a_hang_or_a_crash(hostile: str) -> None:
    with pytest.raises(asn1mod.ModuleError):
        asn1mod.unwrap_html(hostile.encode())  # NUL is caught here
        asn1mod.parse_modules(hostile)


def test_limits_bound_size_and_token_count() -> None:
    with pytest.raises(asn1mod.ModuleError, match="limit"):
        asn1mod.unwrap_html(b"x" * 100, asn1mod.Limits(max_octets=10))
    with pytest.raises(asn1mod.ModuleError, match="tokens"):
        asn1mod.tokenize("a " * 50, asn1mod.Limits(max_tokens=10))
    deep = "M DEFINITIONS ::= BEGIN A ::= " + "(" * 100 + ")" * 100 + " END"
    with pytest.raises(asn1mod.ModuleError, match="nesting"):
        asn1mod.parse_modules(deep, limits=asn1mod.Limits(max_depth=32))


def test_script_tags_in_the_wrapper_are_dropped_not_run_or_kept() -> None:
    raw = b"<html><pre>M DEFINITIONS ::= BEGIN <script>alert(1)</script>A ::= INTEGER END</pre></html>"
    text, _ = asn1mod.unwrap_html(raw)
    assert "<script" not in text
    assert asn1mod.parse_modules(text)[0].assignment("A") is not None


# ------------------------------------------------------------------------------------------- listing

DIR = "/ITU-T/formal-language/itu-t/x/x999/"
LISTING = (
    f'<html><body><pre><A HREF="/ITU-T/formal-language/itu-t/x/">[To Parent Directory]</A><br><br>'
    f' 10/6/2020 10:23 AM        &lt;dir&gt; <A HREF="{DIR}2031/">2031</A><br>'
    f'10/22/2026  7:44 PM        14743 <A HREF="{DIR}Widgets.asn">Widgets.asn</A><br>'
    f' 11/2/2026  1:53 PM        15007 <A HREF="{DIR}Widgets.html">Widgets.html</A><br>'
    f' 11/2/2026  1:53 PM        15007 <A HREF="/ITU-T/elsewhere/Evil.html">Evil.html</A><br>'
    f' 11/2/2026  1:53 PM        15007 <A HREF="{DIR}..%2f..%2fx.html">..%2f..%2fx.html</A><br>'
    f' 11/2/2026  1:53 PM        15007 <A HREF="{DIR}Widgets.html">Widgets.html</A><br>'
    "</pre></body></html>"
)


def test_listing_parser_keeps_plain_entries_and_counts_what_it_drops() -> None:
    entries, dropped = formal.parse_listing(LISTING, DIR)
    assert [(e.name, e.directory, e.size) for e in entries] == [
        ("2031", True, 0),
        ("Widgets.asn", False, 14743),
        ("Widgets.html", False, 15007),
    ]
    assert dropped == 3  # a link that leaves the directory, a traversal name, a duplicate


class Fake:
    """A transport over a dict of path -> bytes, recording every request."""

    def __init__(self, files: dict[str, bytes], status: int = 200, final: str | None = None) -> None:
        self.files, self.status, self.final = files, status, final
        self.calls: list[str] = []

    def __call__(self, url: str, max_octets: int) -> formal.Fetched:
        self.calls.append(url)
        relative = url.removeprefix(formal.BASE + formal.ROOT_PATH)
        if relative not in self.files:
            return formal.Fetched(404, b"", url)
        return formal.Fetched(self.status, self.files[relative][: max_octets + 1], self.final or url)


def tree() -> Fake:
    base = "itu-t/x/x999/"
    return Fake(
        {
            "itu-t/": LISTING.replace(DIR, "/ITU-T/formal-language/itu-t/").encode(),
            base: LISTING.encode(),
            base + "2031/": LISTING.replace(DIR, "/ITU-T/formal-language/" + base + "2031/").encode(),
        }
    )


def test_enumeration_is_bounded_and_says_why_it_stopped() -> None:
    fake = tree()
    _, budget, _ = formal.enumerate_tree(
        fake, "itu-t/x/x999/", budget=formal.Budget(max_requests=1), pause=lambda _s: None
    )
    assert budget.stopped and len(fake.calls) == 1


def test_enumeration_walks_directories_and_paces_requests() -> None:
    fake = tree()
    pauses: list[float] = []
    found, budget, _ = formal.enumerate_tree(fake, "itu-t/x/x999/", pause=pauses.append)
    assert not budget.stopped
    assert {a.path for a in found} >= {"itu-t/x/x999/Widgets.html", "itu-t/x/x999/Widgets.asn"}
    assert len(pauses) == len(fake.calls) - 1 and all(p >= 1.0 for p in pauses)


# ------------------------------------------------------------------------------------------- importer


@pytest.fixture
def home(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("ITULIB_HOME", str(tmp_path))
    return tmp_path


PATH = "itu-t/x/x999/2031/Widgets-Core.html"


def pin_for(body: bytes) -> dict[str, formal.Pin]:
    return {PATH: formal.Pin(hashlib.sha256(body).hexdigest(), len(body))}


def test_unpinned_artifacts_are_refused_unless_trusted(home: Path) -> None:
    fake = Fake({PATH: wrap(MODULE)})
    with pytest.raises(formal.FormalError, match="no pinned digest"):
        formal.import_artifact(PATH, fake, pins={})
    assert not fake.calls and not (home / "formal").exists()
    done = formal.import_artifact(PATH, fake, pins={}, trust_first_use=True)
    assert done.pinned is False and done.modules == ("Widgets-Core",)


def test_a_changed_artifact_fails_its_pin_and_writes_nothing(home: Path) -> None:
    body = wrap(MODULE)
    pins = pin_for(body)
    with pytest.raises(formal.FormalError, match="does not match the pinned"):
        formal.import_artifact(PATH, Fake({PATH: wrap(MODULE + "\n-- changed")}), pins=pins)
    assert not (home / "formal").exists()


@pytest.mark.parametrize(
    "path",
    [
        "",
        "../etc/passwd",
        "itu-t/x/../y.html",
        "a/b\\c.html",
        "itu-t//x.html",
        "x" * 200 + ".html",
        "a/" * 9 + "b.html",
    ],
)
def test_paths_that_could_escape_are_refused(home: Path, path: str) -> None:
    with pytest.raises(formal.FormalError):
        formal.import_artifact(path, Fake({}), pins={}, trust_first_use=True)


def test_only_html_is_fetched_because_asn_is_not_served(home: Path) -> None:
    with pytest.raises(formal.FormalError, match=r"\.html"):
        formal.import_artifact("itu-t/x/x999/2031/Widgets-Core.asn", Fake({}), pins={}, trust_first_use=True)


def test_redirects_oversize_errors_and_non_asn_are_refused_without_writing(home: Path) -> None:
    body = wrap(MODULE)
    cases = [
        (Fake({PATH: body}, final="https://evil.example/x"), "redirected"),
        (Fake({PATH: body}, status=500), "HTTP 500"),
        (Fake({}), "HTTP 404"),
        (Fake({PATH: b"x" * (formal.MAX_ARTIFACT_OCTETS + 1)}), "bound"),
        (Fake({PATH: b"<html><pre>just prose, not a module</pre></html>"}), "not readable"),
    ]
    for fake, message in cases:
        with pytest.raises(formal.FormalError, match=message):
            formal.import_artifact(PATH, fake, pins={}, trust_first_use=True)
    assert not (home / "formal").exists()


def test_the_real_transport_refuses_other_hosts_and_schemes() -> None:
    for url in ("http://www.itu.int/x", "https://evil.example/x", "file:///etc/passwd"):
        with pytest.raises(formal.FormalError, match="only https"):
            formal.urllib_transport(url, 10)


# ---------------------------------------------------------------------------------------------- refs


def test_ref_grammar() -> None:
    ref = formal.parse_formal_ref("X.509#2019-10/AuthenticationFramework::Certificate")
    assert (ref.rec, ref.year, ref.month, ref.module, ref.section) == (
        "X.509",
        "2019",
        "10",
        "AuthenticationFramework",
        "Certificate",
    )
    assert formal.parse_formal_ref("X.1080.0#2017-Cor1/M").suffix == "Cor1"
    assert formal.parse_formal_ref("X.509#2019/M").month is None
    for bad in (
        "X.509/M",
        "X.509#19/M",
        "X.509#2019-13/M",
        "X.509#2019/M::",
        "#2019/M",
        "X.509#2019/M::a::b",
        "X.509#2019/../M",
    ):
        with pytest.raises(formal.FormalError):
            formal.parse_formal_ref(bad)


def test_serving_a_module_a_section_and_the_reserved_sections(home: Path) -> None:
    formal.import_artifact(PATH, Fake({PATH: wrap(MODULE)}), pins={}, trust_first_use=True)
    whole = formal.read("X.999#2031-03/Widgets-Core")
    assert whole["oid"] == "2.99.1.7.3" and len(whole["sections"]) == 6  # type: ignore[arg-type]
    assert whole["cite"] == "ITU-T X.999 (03/2031) formal description, module Widgets-Core"
    section = formal.read("X.999#2031/Widgets-Core::Pair")
    assert section["kind"] == "type" and str(section["text"]).startswith("Pair{T, U} ::=")
    assert formal.read("X.999#2031/Widgets-Core::IMPORTS")["imports"][0]["module"] == "Widgets-Base"  # type: ignore[index]
    assert formal.read("X.999#2031/Widgets-Core::EXPORTS")["exports"] is None
    assert "BEGIN" in str(formal.read("X.999#2031/Widgets-Core::HEADER")["text"])


def test_refs_that_do_not_match_are_errors_never_empty_answers(home: Path) -> None:
    formal.import_artifact(PATH, Fake({PATH: wrap(MODULE)}), pins={}, trust_first_use=True)
    for ref, message in (
        ("X.999#2031-04/Widgets-Core", "does not resolve"),  # wrong month for this file
        ("X.999#2030/Widgets-Core", "not imported"),
        ("X.998#2031/Widgets-Core", "not imported"),
        ("X.999#2031/Other", "not imported"),
        ("X.999#2031/Widgets-Core::Missing", "no assignment"),
    ):
        with pytest.raises(formal.FormalError, match=message):
            formal.read(ref)


def test_a_file_edited_after_import_is_refused(home: Path) -> None:
    formal.import_artifact(PATH, Fake({PATH: wrap(MODULE)}), pins={}, trust_first_use=True)
    formal.artifact_file(PATH).write_bytes(wrap(MODULE + "\nExtra ::= NULL\n"))
    with pytest.raises(formal.FormalError, match="no longer match"):
        formal.read("X.999#2031/Widgets-Core")


def test_pinned_entries_name_files_that_could_exist() -> None:
    for path, pin in formal.PINS.items():
        formal._check_path(path)
        assert len(pin.sha256) == 64 and pin.octets > 0


def test_names_with_spaces_are_kept_but_frontpage_leftovers_are_dropped() -> None:
    base = "/ITU-T/formal-language/itu-t/x/x999/2031/"
    page = (
        f' 1/1/2020  1:00 AM            5 <A HREF="{base}Alert%20Message%20v1.2.html">Alert Message v1.2.html</A><br>'
        f' 1/1/2020  1:00 AM        &lt;dir&gt; <A HREF="{base}_vti_cnf/">_vti_cnf</A><br>'
    )
    entries, dropped = formal.parse_listing(page, base)
    assert [e.name for e in entries] == ["Alert Message v1.2.html"] and dropped == 1
    assert formal.artifact_url("a/Alert Message.html").endswith("a/Alert%20Message.html")


def test_a_module_right_after_the_header_link_is_not_swallowed_by_the_comment() -> None:
    """Found on the real X.509 AlgorithmObjectIdentifiers: only `<br>` separated the comment from the module."""
    raw = (
        b"<html><body><pre><i>-- ASN module extracted from <a href='https://www.itu.int/x'>"
        b"ITU-T X.999 (03/2031)</a></i>"
        b"<br><br>Tiny {joint-iso-itu-t example(99) 1}\nDEFINITIONS ::=\nBEGIN\nA ::= NULL\nEND</pre></body></html>"
    )
    text, note = asn1mod.unwrap_html(raw)
    assert note == "X.999 (03/2031)"
    assert asn1mod.parse_modules(text)[0].name == "Tiny"


def test_a_missing_brace_in_the_published_text_still_yields_the_module_with_a_warning() -> None:
    """ITU's X.509 (2000) AttributeCertificateDefinitions is missing a `}`; END must still close the module."""
    module = asn1mod.parse_modules("M DEFINITIONS ::= BEGIN\nA ::= SEQUENCE {\n  x INTEGER\n\nB ::= NULL\nEND")[0]
    assert module.assignment("A") is not None and module.warnings


def test_encoding_definitions_modules_and_iri_headers_are_read() -> None:
    ecn = asn1mod.parse_modules(
        "E {joint-iso-itu-t(2) 1} ENCODING-DEFINITIONS ::= BEGIN\n"
        "IMPORTS #A FROM Other {2 1};\nX #ENCODINGS ::= {a}\nEND"
    )[0]
    assert ecn.imports[0].symbols == ("#A",) and ecn.assignment("X") is not None
    iri = asn1mod.parse_modules('M {2 1} "/ASN.1/M" DEFINITIONS AUTOMATIC TAGS ::= BEGIN A ::= NULL END')[0]
    assert iri.iri == '"/ASN.1/M"' and iri.tagging == "AUTOMATIC"
