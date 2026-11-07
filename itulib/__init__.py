"""itulib: ITU-T recommendations as a local, citation-precise library and MCP server.

X.680 and X.690 are the normative source for BER and DER and are not in the RFC series, so `rfclib` cannot
answer a question about tag-number minimality or DER canonicalisation. This is the same shape of tool pointed
at the other corpus: clause-precise search, paging, citation, and an errata surface.

The corpus is not in this package and cannot be. ITU's own notice, page iii of X.690 (02/2021), forbids
reproduction without written permission, so `fetch` downloads it on the user's machine into `ITULIB_HOME`.
Every entry point raises `CorpusMissing` naming that command rather than returning an empty answer, because a
missing file and a document with nothing to say must never look the same.
"""

from __future__ import annotations

__version__ = "0.1.0"

from .corpus import CorpusMissing, fetch, has, home, require
from .sources import AMENDMENTS, BY_REC, IN_FORCE, SUPERSEDED, Amendment, Edition, current, resolve
from .text import Clause, clauses, find, pages, tidy

__all__ = [
    "__version__",
    "AMENDMENTS",
    "BY_REC",
    "IN_FORCE",
    "SUPERSEDED",
    "Amendment",
    "Clause",
    "CorpusMissing",
    "Edition",
    "clauses",
    "current",
    "fetch",
    "find",
    "has",
    "home",
    "pages",
    "require",
    "resolve",
    "tidy",
]
