"""`itulib` - fetch, index, then ask.

`fetch` and `sync` are the only commands that touch the network, and they write outside the checkout by
default. Everything that reads refuses to answer when the corpus or index is absent, naming the command that
fixes it; an empty result here is always a real empty, never a swallowed failure.

References use one grammar everywhere: `X.690§11.6¶2` (`¶n` is the nth sentence of the extracted clause), or
the looser `X.690 11.6` and `11.6` (which means X.690).
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable

from . import __version__, corpus, index, sources, text
from .errata import errata_text

DEFAULT = "X.690"


def _resolve(ref: str) -> tuple[sources.Edition, str, int | None]:
    rec, number, para = text.parse_ref(ref)
    return sources.resolve(rec or DEFAULT), number, para


def _join(parts: list[str]) -> str:
    return " ".join(parts)


def cmd_info(_args: argparse.Namespace) -> int:
    for item in (*sources.IN_FORCE, *sources.SUPERSEDED):
        state = "fetched" if corpus.has(item) else "-"
        print(f"{item.key:18} {item.status:11} {item.octets:>10,} B  {state:8} {item.title}")
    for amendment in sources.AMENDMENTS:
        fetched = "fetched" if amendment.artifact and corpus.has(amendment) else "-"
        print(f"{amendment.key:18} {amendment.status:11} {'':>12}  {fetched:8} {amendment.label}")
    print(f"corpus home: {corpus.home()}")
    return 0


def cmd_fetch(args: argparse.Namespace) -> int:
    document = sources.resolve_document(args.target)
    path = corpus.fetch(document, refresh=args.refresh)
    print(f"fetched {document.key} -> {path} ({path.stat().st_size:,} B)")
    return 0


def cmd_sync(args: argparse.Namespace) -> int:
    """Fetch and index each in-force edition. One failure is reported and does not stop the rest, and the exit
    status is non-zero if any failed, because a sync that quietly skips reports the same green as one that ran."""
    everything = (*sources.IN_FORCE, *sources.SUPERSEDED)
    targets = (
        [sources.resolve(name) for name in args.targets]
        if args.targets
        else list(everything if args.all else sources.IN_FORCE)
    )
    failed: list[str] = []
    for edition in targets:
        try:
            corpus.fetch(edition)
            count = index.build(edition)
            print(f"{edition.key:16} ok  {count:>5} clauses")
        except (corpus.CorpusMissing, RuntimeError, OSError) as error:
            failed.append(edition.key)
            print(f"{edition.key:16} FAILED  {error}", file=sys.stderr)
    return 3 if failed else 0


def cmd_index(args: argparse.Namespace) -> int:
    edition = sources.resolve(args.edition)
    print(f"{edition.key}: {index.build(edition)} clauses indexed")
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    edition = sources.resolve(args.edition)
    query = _join(args.query)
    hits, relaxed = index.search_mode(edition, query, args.limit)
    if relaxed:
        print("note: no clause contains every term; these contain some of them\n", file=sys.stderr)
    if not hits:
        print(f"{edition.key}: no clause matches {query!r} (this is a real empty: the index is loaded)")
        return 1
    for hit in hits:
        print(f"{index.citation(edition, hit.number)}  {hit.title}\n    {hit.excerpt}\n")
    return 0


def cmd_read(args: argparse.Namespace) -> int:
    ref = _join(args.ref)
    document = next((a for a in sources.AMENDMENTS if a.key == args.ref[0]), None)
    if document is not None:
        print(document.label, "", errata_text(document), sep="\n")
        return 0
    edition, number, para = _resolve(ref)
    if args.view == "normative":
        found = index.normative_statements(edition, number)
        if found is None:
            print(f"{edition.key}: no clause §{number}", file=sys.stderr)
            return 1
        for n, sentence in found:
            print(f"{index.citation(edition, number, n)}\n    {sentence}")
        return 0
    if args.view == "refs":
        return _print_links(edition, number)
    if para is not None:
        one = index.sentence(edition, number, para)
        if one is None:
            print(f"{edition.key}: §{number} has no ¶{para}", file=sys.stderr)
            return 1
        print(f"{index.citation(edition, number, para)}\n\n{one}")
        return 0
    page = index.page(edition, number, start=args.start, max_tokens=args.max_tokens)
    if page is None or page.total == 0:
        kids = index.children(edition, number)
        if kids:
            print(f"{index.citation(edition, number)}: heading only; subclauses:")
            for child, title in kids:
                print(f"  {child:10} {title}")
            return 0
        if page is None:
            print(f"{edition.key}: no clause §{number}", file=sys.stderr)
            return 1
        print(f"{index.citation(edition, number)}  {page.title}: heading with no text and no indexed subclauses")
        return 0
    print(f"{index.citation(edition, page.number)}  {page.title}\n")
    print(page.text)
    if page.next is not None:
        print(f"\n[¶{page.first}-{page.last} of {page.total}; continue with --start {page.next}]")
    extra = index.fragments(edition, number) - 1
    if extra:
        print(
            f"\nwarning: {extra} other extracted fragment(s) share the number {number}; this is the first. "
            "Check the PDF before relying on it.",
            file=sys.stderr,
        )
    return 0


def cmd_cite(args: argparse.Namespace) -> int:
    edition, number, para = _resolve(_join(args.ref))
    if index.read(edition, number) is None:
        print(f"{edition.key}: no clause §{number}; refusing to cite what is not there", file=sys.stderr)
        return 1
    print(index.citation(edition, number, para))
    return 0


def _print_links(edition: sources.Edition, number: str) -> int:
    found = index.links(edition, number)
    if found is None:
        print(f"{edition.key}: no clause §{number}", file=sys.stderr)
        return 1
    print(index.citation(edition, number))
    for label, values in (
        ("points at", found.clauses),
        ("unresolved", found.unresolved),
        ("recommendations", found.recommendations),
        ("standards", found.standards),
        ("cited by", found.cited_by),
    ):
        print(f"  {label:16} {', '.join(values) if values else '-'}")
    return 0


def cmd_compare(args: argparse.Namespace) -> int:
    first, second = sources.resolve(args.edition_a), sources.resolve(args.edition_b)
    _rec, number, _para = text.parse_ref(args.number)
    result = index.compare(first, second, number)
    print(f"{index.citation(first, number)}  ->  {index.citation(second, number)}")
    if not (result.in_a and result.in_b):
        side = first.key if not result.in_a else second.key
        print(f"§{number} does not exist in {side}; the rule may have moved rather than gone.")
        return 1
    if result.same:
        print("identical (ignoring whitespace and case)")
        return 0
    for para, sentence in result.removed:
        print(f"- [¶{para}] {sentence}")
    for para, sentence in result.added:
        print(f"+ [¶{para}] {sentence}")
    return 0


def cmd_links(args: argparse.Namespace) -> int:
    edition, number, _para = _resolve(_join(args.ref))
    return _print_links(edition, number)


def cmd_grep(args: argparse.Namespace) -> int:
    edition = sources.resolve(args.edition)
    hits, truncated = index.grep(edition, args.pattern, max_tokens=args.max_tokens)
    for hit in hits:
        print(f"{index.citation(edition, hit['number'])}\n    {hit['excerpt']}\n")
    if truncated:
        print("[truncated by --max-tokens; narrow the pattern or raise the budget]", file=sys.stderr)
    return 0 if hits else 1


def cmd_browse(args: argparse.Namespace) -> int:
    if not args.path:
        registered = {item.rec.split(".")[0] for item in sources.IN_FORCE}
        for letter, title in sources.SERIES.items():
            print(f"{letter}  {'*' if letter in registered else ' '}  {title}")
        print("\n* = has registered recommendations")
        return 0
    if len(args.path) == 1:
        for item in sources.IN_FORCE:
            if item.rec.startswith(args.path.upper() + "."):
                print(f"{item.rec:8} {'fetched' if corpus.has(item) else '-':8} {item.title}")
        return 0
    for number, title in index.top_level(sources.resolve(args.path), args.depth):
        print(f"{number:10} {title}")
    return 0


def cmd_errata(args: argparse.Namespace) -> int:
    items = [a for a in sources.AMENDMENTS if a.rec == args.rec]
    if not items:
        print(f"{args.rec}: nothing registered", file=sys.stderr)
        return 1
    for item in items:
        state = "fetched" if item.artifact and corpus.has(item) else ("not fetched" if item.artifact else "no id")
        print(f"{item.key}  [{item.status}; {state}]\n    {item.label}")
    return 0


def cmd_mcp(_args: argparse.Namespace) -> int:
    from . import mcp

    try:
        mcp.require_extra()
    except ImportError as error:
        print(error, file=sys.stderr)
        return 2
    mcp.main()
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="itulib", description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--version", action="version", version=f"itulib {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    def add(name: str, handler: Callable[[argparse.Namespace], int], help_text: str) -> argparse.ArgumentParser:
        command = sub.add_parser(name, help=help_text, description=help_text)
        command.set_defaults(handler=handler)
        return command

    add("info", cmd_info, "registered editions, amendments and what is fetched")

    fetch = add("fetch", cmd_fetch, "download one edition or erratum into ITULIB_HOME and verify its digest")
    fetch.add_argument("target", nargs="?", default=DEFAULT, help="edition or erratum key (default X.690)")
    fetch.add_argument("--refresh", action="store_true", help="download again even if present")

    sync = add("sync", cmd_sync, "fetch and index every in-force edition (or those named)")
    sync.add_argument("targets", nargs="*", help="editions to sync (default: every in-force edition)")
    sync.add_argument("--all", action="store_true", help="include superseded editions that have a digest")

    idx = add("index", cmd_index, "build the clause index for a fetched edition")
    idx.add_argument("edition", nargs="?", default=DEFAULT)

    search = add("search", cmd_search, "full-text clause search")
    search.add_argument("edition")
    search.add_argument("query", nargs="+")
    search.add_argument("--limit", type=int, default=8)

    read = add("read", cmd_read, "print a clause (or one sentence, or an erratum) with its citation")
    read.add_argument("ref", nargs="+", help="X.690§11.6, X.690 11.6¶2, 11.6, or an erratum key")
    read.add_argument("--start", type=int, default=1, help="first sentence to print (paging)")
    read.add_argument("--max-tokens", type=int, default=2000)
    read.add_argument("--view", choices=["text", "normative", "refs"], default="text")

    cite = add("cite", cmd_cite, "the citation string for a clause or sentence")
    cite.add_argument("ref", nargs="+")

    compare = add("compare", cmd_compare, "what changed in a clause between two editions")
    compare.add_argument("number")
    compare.add_argument("edition_a", nargs="?", default="X.690#2008-11")
    compare.add_argument("edition_b", nargs="?", default="X.690#2021-02")

    links = add("links", cmd_links, "what a clause points at, and what points at it")
    links.add_argument("ref", nargs="+")

    grep = add("grep", cmd_grep, "regular expression over clause bodies")
    grep.add_argument("edition")
    grep.add_argument("pattern")
    grep.add_argument("--max-tokens", type=int, default=1500)

    browse = add("browse", cmd_browse, "ITU-T series, a series' recommendations, or a recommendation's clauses")
    browse.add_argument("path", nargs="?", default="")
    browse.add_argument("--depth", type=int, default=2)

    errata = add("errata", cmd_errata, "errata, corrigenda and amendments registered for a recommendation")
    errata.add_argument("rec", nargs="?", default=DEFAULT)

    add("mcp", cmd_mcp, "serve the MCP tools over stdio (needs the mcp extra)")
    return parser


def main(argv: list[str] | None = None) -> int:
    # The corpus is full of characters cp1252 has no room for: X.680 §47.3 contains U+2212 MINUS SIGN, and
    # printing that clause killed the command with UnicodeEncodeError on a redirected Windows console. A tool
    # whose whole job is to hand back clause text cannot be allowed to die on a minus sign, so stdout is
    # UTF-8 with replacement rather than whatever the console's code page happens to be.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
    args = build_parser().parse_args(argv)
    # A missing corpus is a known state with a known remedy, so it is reported as one rather than as a
    # traceback: a stack ending in CorpusMissing reads like a crash, "run: itulib sync" reads as instructions.
    try:
        return int(args.handler(args))
    except KeyError as error:
        print(error.args[0], file=sys.stderr)
        return 2
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2
    except (corpus.CorpusMissing, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
