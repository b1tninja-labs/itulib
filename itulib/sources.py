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
    sha256: str = ""
    octets: int = 0

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
    Edition(
        key="X.681#2021-02",
        rec="X.681",
        edition="02/2021",
        title="Information object specification",
        status="in force",
        artifact="T-REC-X.681-202102-I!!PDF-E",
        sha256="fec21841db1bb8bfc109c21590a531bfefabeb029df5218e6cd6264b0148e32e",
        octets=651_756,
        note="Catalog sync 2026-11-07: id taken from the ITU component page, digest from the bytes downloaded.",
    ),
    Edition(
        key="X.682#2021-02",
        rec="X.682",
        edition="02/2021",
        title="Constraint specification",
        status="in force",
        artifact="T-REC-X.682-202102-I!!PDF-E",
        sha256="3b8a035c654f1b0247043f02f337de9eedf4494d86314e82f21824d1ffd3585e",
        octets=572_419,
        note="Catalog sync 2026-11-07: id taken from the ITU component page, digest from the bytes downloaded.",
    ),
    Edition(
        key="X.683#2021-02",
        rec="X.683",
        edition="02/2021",
        title="Parameterization of ASN.1 specifications",
        status="in force",
        artifact="T-REC-X.683-202102-I!!PDF-E",
        sha256="2d81b95c04e0aabc158a0290a62f993c8a0d9a7d170a4130603f71cd942481f2",
        octets=480_930,
        note="Catalog sync 2026-11-07: id taken from the ITU component page, digest from the bytes downloaded.",
    ),
    Edition(
        key="X.691#2021-02",
        rec="X.691",
        edition="02/2021",
        title="ASN.1 encoding rules: Packed Encoding Rules (PER)",
        status="in force",
        artifact="T-REC-X.691-202102-I!!PDF-E",
        sha256="cd0a5f51e2840346c5408a9ca90623b3437625b55d1a166e43d05a8ceeb6de86",
        octets=1_074_443,
        note="Catalog sync 2026-11-07: id taken from the ITU component page, digest from the bytes downloaded.",
    ),
    Edition(
        key="X.692#2021-02",
        rec="X.692",
        edition="02/2021",
        title="ASN.1 encoding rules: Encoding Control Notation (ECN)",
        status="in force",
        artifact="T-REC-X.692-202102-I!!PDF-E",
        sha256="14516d83f16ec49c710573ad0c6ea61de9b0461962d4618c9cf00433e74a6829",
        octets=2_447_703,
        note="Catalog sync 2026-11-07: id taken from the ITU component page, digest from the bytes downloaded.",
    ),
    Edition(
        key="X.693#2021-02",
        rec="X.693",
        edition="02/2021",
        title="ASN.1 encoding rules: XML Encoding Rules (XER)",
        status="in force",
        artifact="T-REC-X.693-202102-I!!PDF-E",
        sha256="e548bbfeedc46db3fd85ff7d3ee1396538024b8d5f2dd77ecb96df3dccf6ac67",
        octets=1_104_226,
        note="Catalog sync 2026-11-07: id taken from the ITU component page, digest from the bytes downloaded.",
    ),
    Edition(
        key="X.694#2021-02",
        rec="X.694",
        edition="02/2021",
        title="ASN.1 encoding rules: Mapping W3C XML schema definitions into ASN.1",
        status="in force",
        artifact="T-REC-X.694-202102-I!!PDF-E",
        sha256="7cd4dd981421fb85d68182381e8edbd3d07dd9a3e9ff1ab7fd690e642625aa7a",
        octets=1_745_448,
        note="Catalog sync 2026-11-07: id taken from the ITU component page, digest from the bytes downloaded.",
    ),
    Edition(
        key="X.695#2021-02",
        rec="X.695",
        edition="02/2021",
        title="ASN.1 encoding rules: Registration and application of PER encoding instructions",
        status="in force",
        artifact="T-REC-X.695-202102-I!!PDF-E",
        sha256="7f843bfab8bf332c0aaf953ae396cf4133d18dfdd40e24ce0e681dc7422e799a",
        octets=629_992,
        note="Catalog sync 2026-11-07: id taken from the ITU component page, digest from the bytes downloaded.",
    ),
    Edition(
        key="X.696#2021-02",
        rec="X.696",
        edition="02/2021",
        title="ASN.1 encoding rules: Specification of Octet Encoding Rules (OER)",
        status="in force",
        artifact="T-REC-X.696-202102-I!!PDF-E",
        sha256="aa6ead13c19524fb087f0a376272e11c2c87d0dfc9fb6e26ef154df5b909c2c4",
        octets=777_091,
        note="Catalog sync 2026-11-07: id taken from the ITU component page, digest from the bytes downloaded.",
    ),
    Edition(
        key="X.697#2021-02",
        rec="X.697",
        edition="02/2021",
        title="ASN.1 encoding rules: Specification of JavaScript Object Notation Encoding Rules (JER)",
        status="in force",
        artifact="T-REC-X.697-202102-I!!PDF-E",
        sha256="9b4a335e29d7ff71c9c29ad19d96f9b0c4b98fb1a0dfcc0a63cdd9333cf798b6",
        octets=745_268,
        note="Catalog sync 2026-11-07: id taken from the ITU component page, digest from the bytes downloaded.",
    ),
)

SUPERSEDED: tuple[Edition, ...] = (
    Edition(
        key="X.690#2015-08",
        rec="X.690",
        edition="08/2015",
        title="ASN.1 encoding rules: BER, CER and DER",
        status="superseded",
        artifact="T-REC-X.690-201508-S!!PDF-E",
        sha256="5b61e6a08ee78b7eb3cee4215916647c5f30cb6e36b59348a25d61fa988cb529",
        octets=935_416,
        note="Superseded editions are listed under a -S id, not -I: the -I form returns 'Document Not Found'. "
        "Digest measured 2026-11-07; 38 pages.",
    ),
    Edition(
        key="X.690#2008-11",
        rec="X.690",
        edition="11/2008",
        title="ASN.1 encoding rules: BER, CER and DER",
        status="superseded",
        artifact="T-REC-X.690-200811-S!!PDF-E",
        sha256="56b3a3f95ab19bbf521f3242756191a3bbf7ee0fb352290cee301c542b3b3a86",
        octets=203_955,
        note="The edition most legacy Python codecs were written against. This is the base text: Corrigenda 1 "
        "(10/11) and 2 (03/14) are separate documents and are not applied to it. Digest measured 2026-11-07; "
        "38 pages.",
    ),
)

AMENDMENTS: tuple[Amendment, ...] = (
    Amendment(
        key="X.690#2021-02!erratum-1",
        rec="X.690",
        label="Erratum 1 (09/2021) to Rec. X.690 (2021) | ISO/IEC 8825-1:2021",
        status="in force",
        artifact="T-REC-X.690-202109-I!Err1!PDF-E",
        note="Listed In force on the X.690 page. A one-page covering note, 13 September 2021: Figure 4 "
        "(high-tag-number identifier octets) has a typo in its penultimate octet and is replaced. The id is "
        "read off the erratum's own page; the `!!ERSN1-E` and `!!DOC-E` guesses return HTTP 500.",
        sha256="bb1acaa66a0897f9e53569d3449ce8fbf0892243ddd0cc430c912ed3178d6835",
        octets=194_138,
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

# ITU-T recommendation series, as titled on https://www.itu.int/rec/T-REC/en (read 2026-11-07). There is no
# B, C or W series. L's title is truncated on the page and is kept truncated rather than completed from memory.
SERIES: dict[str, str] = {
    "A": "Organization of the work of ITU-T",
    "D": "Tariff and accounting principles and international telecommunication/ICT economic and policy issues",
    "E": "Overall network operation, telephone service, service operation and human factors",
    "F": "Non-telephone telecommunication services",
    "G": "Transmission systems and media, digital systems and networks",
    "H": "Audiovisual and multimedia systems",
    "I": "Integrated services digital network",
    "J": "Cable networks and transmission of television, sound programme and other multimedia signals",
    "K": "Protection against interference",
    "L": "Environment and ICTs, climate change, e-waste, energy efficiency; construction, ... (title truncated)",
    "M": "Telecommunication management, including TMN and network maintenance",
    "N": "Maintenance: international sound programme and television transmission circuits",
    "O": "Specifications of measuring equipment",
    "P": "Telephone transmission quality, telephone installations, local line networks",
    "Q": "Switching and signalling, and associated measurements and tests",
    "R": "Telegraph transmission",
    "S": "Telegraph services terminal equipment",
    "T": "Terminals for telematic services",
    "U": "Telegraph switching",
    "V": "Data communication over the telephone network",
    "X": "Data networks, open system communications and security",
    "Y": "Global information infrastructure, Internet protocol aspects, next-generation networks, "
    "Internet of Things and smart cities",
    "Z": "Languages and general software aspects for telecommunication systems",
}

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


def resolve_document(key: str) -> Edition | Amendment:
    """An edition, or an amendment/erratum when the key names one (`X.690#2021-02!erratum-1`)."""
    for amendment in AMENDMENTS:
        if amendment.key == key:
            return amendment
    return resolve(key)


def resolve(key: str) -> Edition:
    """Look an edition up by `rec` or by `rec#edition`. Ambiguity is an error, not a guess."""
    for edition in (*IN_FORCE, *SUPERSEDED):
        if edition.key == key or edition.rec == key:
            return edition
    raise KeyError(f"unknown edition {key!r}; registered: {', '.join(e.key for e in (*IN_FORCE, *SUPERSEDED))}")
