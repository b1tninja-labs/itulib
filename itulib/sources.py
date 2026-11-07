"""The edition registry: what exists, where it comes from, and what it hashed to.

Every URL and digest here was fetched on 2026-11-07, not recalled. The superseded editions are listed with
their amendments because asn1core's questions are edition-sensitive: X.690 (02/21) is not what a 2008-era
decoder was written against, and Amendment 2 (06/06) "Time type support" is exactly the kind of change that
moves a rule between editions.
"""

from __future__ import annotations

from dataclasses import dataclass

DOLOGIN = "https://www.itu.int/rec/dologin_pub.asp?lang=e&id={artifact}&type=items"


@dataclass(frozen=True)
class Edition:
    """One published edition of one recommendation."""

    key: str
    rec: str
    edition: str
    title: str
    status: str
    artifact: str
    sha256: str
    octets: int
    note: str = ""

    @property
    def pdf_url(self) -> str:
        return DOLOGIN.format(artifact=self.artifact)


@dataclass(frozen=True)
class Amendment:
    """An amendment, corrigendum or erratum attached to an edition."""

    key: str
    rec: str
    label: str
    status: str
    artifact: str | None
    note: str = ""

    @property
    def pdf_url(self) -> str | None:
        return DOLOGIN.format(artifact=self.artifact) if self.artifact else None


IN_FORCE: tuple[Edition, ...] = (
    Edition(
        key="X.690#2021-02",
        rec="X.690",
        edition="02/2021",
        title="ASN.1 encoding rules: BER, CER and DER",
        status="in force",
        artifact="T-REC-X.690-202102-I!!PDF-E",
        sha256="6ac799a2d1ebed36abe39c9eac3586185bfb7db679f801e737189d6fdb1bbd6c",
        octets=840_764,
        note="Joint designation ISO/IEC 8825-1:2021. Verified: 38 pages, 98,873 characters extract.",
    ),
    Edition(
        key="X.680#2021-02",
        rec="X.680",
        edition="02/2021",
        title="ASN.1: Specification of basic notation",
        status="in force",
        artifact="T-REC-X.680-202102-I!!PDF-E",
        sha256="b69dc4754f0709a7e344c886f277ed9e37a4336029593ba91bc6df6065f9ee14",
        octets=2_088_934,
        note="Joint designation ISO/IEC 8824-1:2021. Owns the restricted string alphabets X.690 defers to.",
    ),
)

SUPERSEDED: tuple[Edition, ...] = (
    Edition(
        key="X.690#2015-08",
        rec="X.690",
        edition="08/2015",
        title="ASN.1 encoding rules: BER, CER and DER",
        status="superseded",
        artifact="T-REC-X.690-201508-I!!PDF-E",
        sha256="",
        octets=0,
        note="Digest not captured; fetch verifies size only until a digest is recorded.",
    ),
    Edition(
        key="X.690#2008-11",
        rec="X.690",
        edition="11/2008",
        title="ASN.1 encoding rules: BER, CER and DER",
        status="superseded",
        artifact="T-REC-X.690-200811-I!!PDF-E",
        sha256="",
        octets=0,
        note="Digest not captured; fetch verifies size only until a digest is recorded. The edition most "
        "legacy Python codecs were written against. Corrigenda 1 (10/11) and 2 (03/14).",
    ),
)

AMENDMENTS: tuple[Amendment, ...] = (
    Amendment(
        key="X.690#2021-02!erratum-1",
        rec="X.690",
        label="Erratum 1 (09/2021) to Rec. X.690 (2021) | ISO/IEC 8825-1:2021",
        status="in force",
        artifact=None,
        note="Listed In force on the X.690 page. The format id guessed here returned HTTP 500; discover the "
        "real id from the component page before fetching. rfclib-style errata surface depends on this.",
    ),
    Amendment(
        key="X.690#2002-07!amd2",
        rec="X.690",
        label="Amendment 2 (06/2006) Time type support",
        status="superseded",
        artifact=None,
        note="Relevant to the UTCTime/GeneralizedTime rows: the time rules moved editions, so a row resolved "
        "against 02/2021 may not describe what an older decoder implemented.",
    ),
)

BY_REC: dict[str, tuple[Edition, ...]] = {}
for _edition in (*IN_FORCE, *SUPERSEDED):
    BY_REC.setdefault(_edition.rec, ())
    BY_REC[_edition.rec] = (*BY_REC[_edition.rec], _edition)


def current(rec: str) -> Edition:
    """The in-force edition of a recommendation, or KeyError. Never a silent default."""
    for edition in IN_FORCE:
        if edition.rec == rec:
            return edition
    raise KeyError(f"{rec}: no in-force edition registered")


def resolve(key: str) -> Edition:
    """Look an edition up by `rec` or by `rec#edition`. Ambiguity is an error, not a guess."""
    for edition in (*IN_FORCE, *SUPERSEDED):
        if edition.key == key or edition.rec == key:
            return edition
    raise KeyError(f"unknown edition {key!r}; registered: {', '.join(e.key for e in (*IN_FORCE, *SUPERSEDED))}")
