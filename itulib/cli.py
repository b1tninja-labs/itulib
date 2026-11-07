"""`python -m itulib.cli` - fetch, index, then ask.

`fetch` is the only command that touches the network, and it writes outside the checkout by default. Search
and read refuse to answer when the corpus or index is absent, naming the command that fixes it; an empty
result here is always a real empty, never a swallowed failure.
"""

from __future__ import annotations

import argparse
import sys

from . import corpus, index, sources
from .errata import errata_text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="itulib", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    for name, help_text in (
        ("fetch", "download an edition into ITULIB_HOME and verify its digest"),
        ("index", "build the clause index for a fetched edition"),
        ("search", "full-text clause search"),
        ("read", "print one clause with its citation"),
        ("info", "registered editions, statuses and amendments"),
    ):
        command = sub.add_parser(name, help=help_text)
        command.add_argument("args", nargs="*", help="edition key (default X.690) and query")

    args = parser.parse_args(argv)
    key = args.args[0] if args.args else "X.690"

    try:
        edition = sources.resolve_document(key)
    except KeyError as error:
        print(error, file=sys.stderr)
        return 2

    if args.command == "info":
        for item in (*sources.IN_FORCE, *sources.SUPERSEDED):
            print(f"{item.key:18} {item.status:11} {item.octets:>10,} B  {item.title}")
        for amendment in sources.AMENDMENTS:
            fetched = "fetched" if amendment.artifact and corpus.has(amendment) else "not fetched"
            print(f"{amendment.key:18} {amendment.status:11} {amendment.label} [{fetched}]")
        print(f"corpus home: {corpus.home()}  present: {[e.key for e in (*sources.IN_FORCE,) if corpus.has(e)]}")
        return 0

    if args.command == "fetch":
        path = corpus.fetch(edition)
        print(f"fetched {edition.key} -> {path} ({path.stat().st_size:,} B)")
        return 0

    if isinstance(edition, sources.Amendment):
        # An erratum has no clause structure to index; `read` prints its extracted text, nothing else applies.
        if args.command != "read":
            print(f"{edition.key} is an erratum or amendment: only `fetch` and `read` apply", file=sys.stderr)
            return 2
        try:
            print(edition.label)
            print()
            print(errata_text(edition))
        except (corpus.CorpusMissing, RuntimeError) as error:
            print(str(error), file=sys.stderr)
            return 3
        return 0

    # Everything below reads the corpus. A missing corpus is a known state with a known remedy, so it is
    # reported as one rather than as a traceback - the same rule mcp.py follows, and the reason it exists is
    # that a stack ending in CorpusMissing reads like a crash while "run: python -m itulib.cli fetch X.680"
    # reads as instructions.
    try:
        return _corpus_command(args, edition)
    except (corpus.CorpusMissing, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 3


def _corpus_command(args: argparse.Namespace, edition: sources.Edition) -> int:
    if args.command == "index":
        count = index.build(edition)
        print(f"{edition.key}: {count} clauses indexed")
        return 0

    if args.command == "search":
        query = " ".join(args.args[1:]) or "BOOLEAN"
        hits = index.search(edition, query)
        if not hits:
            print(f"{edition.key}: no clause matches {query!r} (this is a real empty: the index is loaded)")
            return 1
        for hit in hits:
            print(f"§{hit.number} {hit.title}\n    {hit.excerpt}\n")
        return 0

    if args.command == "read":
        if len(args.args) < 2:
            print("usage: itulib read X.690 11.1", file=sys.stderr)
            return 2
        clause = index.read(edition, args.args[1])
        if clause is None:
            print(f"{edition.key}: no clause §{args.args[1]}", file=sys.stderr)
            return 1
        print(f"{clause.cite(edition.key)} {clause.title}\n\n{clause.body}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
