"""Reading an ASN.1 module as a document: header, IMPORTS, EXPORTS, and one section per assignment.

This is a structural reader, not a validator. It finds the boundaries the module itself draws - the module
reference and its object identifier, the IMPORTS clause, the EXPORTS clause, and where each `Name ::= ...`
assignment begins and ends - and hands back the original text of each piece. It never interprets types, so a
construct it does not know about costs nothing worse than a coarser section. `asn1core` decides what is valid.

The input is hostile by assumption: it came over the network from a third party, or from a file a user pointed
at. So every loop is bounded by the input length, nesting is a counter rather than recursion, and the limits in
`Limits` turn pathological input into `ModuleError`, never into a hang or an unbounded allocation.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field

ROOT_ARCS = {
    "itu-t": 0,
    "ccitt": 0,
    "iso": 1,
    "joint-iso-itu-t": 2,
    "joint-iso-ccitt": 2,
}


class ModuleError(ValueError):
    """The text is not an ASN.1 module this reader can take apart, or it exceeds a limit."""


@dataclass(frozen=True)
class Limits:
    max_octets: int = 2 * 1024 * 1024
    max_tokens: int = 400_000
    max_depth: int = 64
    max_assignments: int = 20_000
    max_modules: int = 64


DEFAULT_LIMITS = Limits()


@dataclass(frozen=True)
class Token:
    text: str
    start: int
    end: int
    line: int
    first_on_line: bool


@dataclass(frozen=True)
class Import:
    symbols: tuple[str, ...]
    module: str
    oid_text: str | None
    with_successors: bool = False


@dataclass(frozen=True)
class Assignment:
    name: str
    kind: str  # type | class | value | set
    parameterised: bool
    start: int
    end: int
    line: int
    text: str


@dataclass
class Module:
    name: str
    oid_text: str | None
    oid: str | None
    tagging: str | None
    extensibility_implied: bool
    exports: str | tuple[str, ...] | None  # None: no EXPORTS clause (everything is exported)
    imports: tuple[Import, ...]
    assignments: tuple[Assignment, ...]
    iri: str | None = None
    edition_note: str | None = None
    source: str = ""
    warnings: list[str] = field(default_factory=list)

    def assignment(self, name: str) -> Assignment | None:
        for item in self.assignments:
            if item.name == name:
                return item
        return None


# ---------------------------------------------------------------------------------------------------- unwrap

_TAG = re.compile(r"<[^>]{0,2000}>")
_BREAK = re.compile(r"<br\s*/?>", re.IGNORECASE)
_ACTIVE = re.compile(r"<(script|style)\b.{0,200000}?</\1\s*>", re.IGNORECASE | re.DOTALL)
_HEADER_EDITION = re.compile(r"ITU-T\s+([A-Z]\.\d+(?:\.\d+)?)\s*\((\d{2})/(\d{4})\)")


def unwrap_html(raw: bytes, limits: Limits = DEFAULT_LIMITS) -> tuple[str, str | None]:
    """Source text of a module published inside an HTML wrapper, and the edition its header names.

    ITU serves each module as `<html><body><pre>...</pre></body></html>` with one comment line linking to
    the Recommendation. Tags are dropped without being interpreted, entities are decoded, and nothing in the
    wrapper is ever executed or followed. Plain text with no wrapper passes through unchanged.
    """
    if len(raw) > limits.max_octets:
        raise ModuleError(f"{len(raw)} octets exceeds the {limits.max_octets} limit")
    if b"\x00" in raw:
        raise ModuleError("NUL octet in module text")
    text = raw.decode("utf-8", errors="replace")
    stripped = text.lstrip()
    if stripped[:5].lower() in {"<html", "<!doc"} or stripped.lower().startswith("<pre"):
        start = stripped.lower().find("<pre")
        body = stripped[start:] if start >= 0 else stripped
        end = body.lower().rfind("</pre>")
        if end >= 0:
            body = body[:end]
        text = html.unescape(_TAG.sub("", _BREAK.sub("\n", _ACTIVE.sub("", body))))
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    found = _HEADER_EDITION.search(text[:4000])
    note = f"{found.group(1)} ({found.group(2)}/{found.group(3)})" if found else None
    return text, note


# ------------------------------------------------------------------------------------------------- tokenizer

_IDENT = re.compile(r"#?[A-Za-z](?:[A-Za-z0-9]|-(?!-))*")
_NUMBER = re.compile(r"\d+")
_QUOTED = re.compile(r"'[0-9A-Fa-f01\s]*'[BbHh]")


def tokenize(text: str, limits: Limits = DEFAULT_LIMITS) -> list[Token]:
    """Tokens with comments removed. Comments and strings are skipped, never recursed into."""
    tokens: list[Token] = []
    pos, line, n = 0, 1, len(text)
    first = True
    while pos < n:
        ch = text[pos]
        if ch == "\n":
            line += 1
            pos += 1
            first = True
            continue
        if ch in " \t\f\v":
            pos += 1
            continue
        if text.startswith("--", pos):
            pos += 2
            while pos < n and text[pos] != "\n" and not text.startswith("--", pos):
                pos += 1
            if text.startswith("--", pos):
                pos += 2
            continue
        if text.startswith("/*", pos):
            depth = 1
            pos += 2
            while pos < n and depth:
                if text.startswith("/*", pos):
                    depth += 1
                    pos += 2
                elif text.startswith("*/", pos):
                    depth -= 1
                    pos += 2
                else:
                    if text[pos] == "\n":
                        line += 1
                        first = True
                    pos += 1
            if depth:
                raise ModuleError(f"unterminated /* comment (line {line})")
            continue
        start = pos
        if ch == '"':
            pos += 1
            while True:
                end = text.find('"', pos)
                if end < 0:
                    raise ModuleError(f"unterminated string (line {line})")
                pos = end + 1
                if text.startswith('"', pos):
                    pos += 1
                    continue
                break
            line += text.count("\n", start, pos)
        elif text.startswith("::=", pos) or text.startswith("...", pos):
            pos += 3
        elif text.startswith("..", pos):
            pos += 2
        elif (
            (ch == "'" and (m := _QUOTED.match(text, pos)))
            or (m := _IDENT.match(text, pos))
            or (m := _NUMBER.match(text, pos))
        ):
            pos = m.end()
        else:
            pos += 1
        tokens.append(Token(text[start:pos], start, pos, line, first))
        first = False
        if len(tokens) > limits.max_tokens:
            raise ModuleError(f"more than {limits.max_tokens} tokens")
    return tokens


_OPEN = {"{": "}", "(": ")", "[": "]"}
_CLOSE = {"}", ")", "]"}


# ----------------------------------------------------------------------------------------------------- parse


def _oid_numeric(arcs_text: str) -> str | None:
    inner = arcs_text.strip()[1:-1]
    parts = re.findall(r"[A-Za-z][A-Za-z0-9-]*\s*\(\s*\d+\s*\)|[A-Za-z][A-Za-z0-9-]*|\d+", inner)
    numbers: list[str] = []
    for index, part in enumerate(parts):
        named = re.fullmatch(r"([A-Za-z][A-Za-z0-9-]*)\s*\(\s*(\d+)\s*\)", part)
        if named:
            numbers.append(named.group(2))
        elif part.isdigit():
            numbers.append(part)
        elif index == 0 and part in ROOT_ARCS:
            numbers.append(str(ROOT_ARCS[part]))
        else:
            return None
    return ".".join(numbers) if numbers else None


def _classify(left: list[Token], right: list[Token]) -> tuple[str, bool]:
    name = left[0].text
    # `Name {A, B} ::=` is a parameterised definition; `Name CLASS-NAME ::=` is an object set.
    parameterised = len(left) > 1 and left[1].text == "{"
    if name[0].islower():
        return "value", False
    if len(left) == 1:
        return (
            "class" if right and right[0].text in {"CLASS", "TYPE-IDENTIFIER", "ABSTRACT-SYNTAX"} else "type"
        ), False
    if parameterised:
        closer = _match(left, 1)
        if closer == len(left) - 1:
            return ("class" if right and right[0].text == "CLASS" else "type"), True
    return "set", False


def _match(tokens: list[Token], index: int) -> int:
    depth = 0
    for i in range(index, len(tokens)):
        if tokens[i].text in _OPEN:
            depth += 1
        elif tokens[i].text in _CLOSE:
            depth -= 1
            if depth == 0:
                return i
    return len(tokens) - 1


def _braced(tokens: list[Token], index: int, text: str, limits: Limits) -> tuple[str, int]:
    """Text of the bracketed group starting at tokens[index], and the index after it."""
    depth = 0
    for i in range(index, len(tokens)):
        t = tokens[i].text
        if t in _OPEN:
            depth += 1
            if depth > limits.max_depth:
                raise ModuleError(f"nesting deeper than {limits.max_depth} (line {tokens[i].line})")
        elif t in _CLOSE:
            depth -= 1
            if depth == 0:
                return text[tokens[index].start : tokens[i].end], i + 1
    raise ModuleError(f"unbalanced bracket (line {tokens[index].line})")


def _parse_imports(tokens: list[Token], i: int, text: str, limits: Limits) -> tuple[list[Import], int]:
    """tokens[i] is the first token after IMPORTS. Returns the clauses and the index after the `;`."""
    result: list[Import] = []
    symbols: list[str] = []
    n = len(tokens)
    while i < n:
        t = tokens[i].text
        if t == ";":
            return result, i + 1
        if t == ",":
            i += 1
        elif t == "FROM":
            i += 1
            if i >= n or not tokens[i].text.lstrip("#")[:1].isalpha():
                raise ModuleError(f"IMPORTS: FROM without a module (line {tokens[i - 1].line})")
            module = tokens[i].text
            i += 1
            oid = None
            if i < n and tokens[i].text == "{":
                oid, i = _braced(tokens, i, text, limits)
            elif (
                i + 1 < n
                and tokens[i].text[:1].islower()
                and tokens[i + 1].text not in {",", "FROM"}
                and tokens[i + 1].text[:1] != ","
            ):
                oid = tokens[i].text
                i += 1
            successors = False
            if i + 1 < n and tokens[i].text == "WITH" and tokens[i + 1].text in {"SUCCESSORS", "DESCENDANTS"}:
                successors = True
                i += 2
            result.append(Import(tuple(symbols), module, oid, successors))
            symbols = []
        elif t == "{":
            # a parameterised import `Name{}`: keep the braces on the symbol
            group, i = _braced(tokens, i, text, limits)
            if symbols:
                symbols[-1] += group
        elif t[:1].isalpha() or t[:1] == "#":
            symbols.append(t)
            i += 1
        else:
            raise ModuleError(f"IMPORTS: unexpected {t!r} (line {tokens[i].line})")
        if len(result) > limits.max_assignments:
            raise ModuleError("IMPORTS: too many clauses")
    raise ModuleError("IMPORTS clause has no terminating ';'")


def parse_modules(text: str, *, limits: Limits = DEFAULT_LIMITS) -> list[Module]:
    """Every module in `text`, in order. At least one is required."""
    tokens = tokenize(text, limits)
    modules: list[Module] = []
    i, n = 0, len(tokens)
    while i < n:
        if len(modules) >= limits.max_modules:
            raise ModuleError(f"more than {limits.max_modules} modules in one file")
        if not tokens[i].text[:1].isupper():
            i += 1
            continue
        # header: Name [{oid}] DEFINITIONS [tagging] [EXTENSIBILITY IMPLIED] ::= BEGIN
        name = tokens[i].text
        j = i + 1
        oid_text = None
        if j < n and tokens[j].text == "{":
            oid_text, j = _braced(tokens, j, text, limits)
        iri = None
        if j < n and tokens[j].text.startswith('"'):  # an IRI value after the OID (X.680 module header)
            iri = tokens[j].text
            j += 1
        if not (j < n and tokens[j].text in {"DEFINITIONS", "ENCODING-DEFINITIONS"}):
            i += 1
            continue
        j += 1
        tagging = None
        implied = False
        while j < n and tokens[j].text != "::=":
            word = tokens[j].text
            if word in {"EXPLICIT", "IMPLICIT", "AUTOMATIC"}:
                tagging = word
            elif word == "EXTENSIBILITY":
                implied = True
            elif word not in {"TAGS", "IMPLIED"}:
                raise ModuleError(f"module header: unexpected {word!r} (line {tokens[j].line})")
            j += 1
        if not (j + 1 < n and tokens[j].text == "::=" and tokens[j + 1].text == "BEGIN"):
            raise ModuleError(f"module {name}: DEFINITIONS without ::= BEGIN")
        j += 2
        body_start = j
        # body: everything to the END that closes it, tracking bracket depth
        depth = 0
        k = j
        end_index = -1
        unbalanced = False
        while k < n:
            t = tokens[k].text
            if t in _OPEN:
                depth += 1
                if depth > limits.max_depth:
                    raise ModuleError(f"nesting deeper than {limits.max_depth} (line {tokens[k].line})")
            elif t in _CLOSE:
                depth = max(0, depth - 1)
            elif t == "END" and (depth == 0 or tokens[k].first_on_line):
                # END is reserved, so one starting a line closes the module even inside an unclosed bracket:
                # ITU publishes at least one module with a missing brace (X.509 (2000) AttributeCertificate
                # Definitions), and refusing the whole module for it would hide every other assignment.
                if depth:
                    unbalanced = True
                end_index = k
                break
            k += 1
        if end_index < 0:
            raise ModuleError(f"module {name}: no END")
        module = _parse_body(name, oid_text, tagging, implied, tokens[body_start:end_index], text, limits)
        module.iri = iri
        if unbalanced:
            module.warnings.append(
                "unbalanced brackets in the published text; later assignments may be merged into one section"
            )
        modules.append(module)
        i = end_index + 1
    if not modules:
        raise ModuleError("no module found: expected `Name {oid} DEFINITIONS ::= BEGIN ... END`")
    return modules


def _parse_body(
    name: str,
    oid_text: str | None,
    tagging: str | None,
    implied: bool,
    body: list[Token],
    text: str,
    limits: Limits,
) -> Module:
    exports: str | tuple[str, ...] | None = None
    imports: list[Import] = []
    i, n = 0, len(body)
    if i < n and body[i].text == "EXPORTS":
        i += 1
        names: list[str] = []
        while i < n and body[i].text != ";":
            if body[i].text != ",":
                names.append(body[i].text)
            i += 1
        i += 1
        exports = "all" if names == ["All"] else tuple(names)
    if i < n and body[i].text == "IMPORTS":
        imports, i = _parse_imports(body, i + 1, text, limits)
    # assignments: depth-0 `::=` tokens; each assignment begins at the first token of its line
    marks: list[int] = []
    depth = 0
    for k in range(i, n):
        t = body[k].text
        if t in _OPEN:
            depth += 1
        elif t in _CLOSE:
            depth = max(0, depth - 1)
        elif t == "::=" and depth == 0:
            marks.append(k)
            if len(marks) > limits.max_assignments:
                raise ModuleError(f"more than {limits.max_assignments} assignments")
    starts: list[int] = []
    floor = i
    for mark in marks:
        s = mark - 1
        while s > floor and not body[s].first_on_line:
            s -= 1
        # a left side that wraps: `Name\n  {params} ::=` or `name\n  Type ::=`
        while s > floor and body[s].text in {"{", "::="}:
            s -= 1
        starts.append(max(s, floor))
        floor = mark + 1
    assignments: list[Assignment] = []
    for index, mark in enumerate(marks):
        s = starts[index]
        e = starts[index + 1] if index + 1 < len(starts) else n
        left, right = body[s:mark], body[mark + 1 : e]
        if not left or not left[0].text[:1].isalpha():
            continue
        kind, parameterised = _classify(left, right)
        end_char = body[e - 1].end if e > mark + 1 else body[mark].end
        assignments.append(
            Assignment(
                name=left[0].text,
                kind=kind,
                parameterised=parameterised,
                start=left[0].start,
                end=end_char,
                line=left[0].line,
                text=text[left[0].start : end_char],
            )
        )
    return Module(
        name=name,
        oid_text=oid_text,
        oid=_oid_numeric(oid_text) if oid_text else None,
        tagging=tagging,
        extensibility_implied=implied,
        exports=exports,
        imports=tuple(imports),
        assignments=tuple(assignments),
    )
