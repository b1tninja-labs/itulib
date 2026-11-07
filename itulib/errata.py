"""The text of an erratum, from the fetched covering note. Not indexed: it has no clause structure."""

from __future__ import annotations

from . import corpus, text
from .sources import Amendment


def errata_text(amendment: Amendment) -> str:
    """Extracted text of a fetched erratum, or CorpusMissing naming the fetch command.

    The covering note is a figure replacement, so the extract carries the instruction and the figure caption
    but not the figure itself; the PDF is the authority for what the corrected figure shows.
    """
    pdf = corpus.require(amendment)
    return text.tidy(" ".join(text.pages(pdf)))
