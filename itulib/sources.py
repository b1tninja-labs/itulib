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
    Edition(
        key="X.500#2019-10",
        rec="X.500",
        edition="10/2019",
        title="The Directory: Overview of concepts, models and services",
        status="in force",
        artifact="T-REC-X.500-201910-I!!PDF-E",
        sha256="616be799e0d7932c203e339f3d5576bd58014711be58558b900f94d46ad9bb98",
        octets=1_761_409,
        note="X.500 catalog sync 2026-11-07: id read off the ITU component page, which lists this PDF as freely "
        "available at 1761409 bytes; digest from the bytes downloaded.",
    ),
    Edition(
        key="X.501#2019-10",
        rec="X.501",
        edition="10/2019",
        title="The Directory: Models",
        status="in force",
        artifact="T-REC-X.501-201910-I!!PDF-E",
        sha256="fa16c552c65a67ed0ab5be0291db368fc38ad94cb64df0bd90a9747586a3751b",
        octets=2_767_911,
        note="X.500 catalog sync 2026-11-07: id read off the ITU component page, which lists this PDF as freely "
        "available at 2767911 bytes; digest from the bytes downloaded.",
    ),
    Edition(
        key="X.508#2024-10",
        rec="X.508",
        edition="10/2024",
        title="The Directory: Key management and public-key infrastructure establishment and maintenance",
        status="in force",
        artifact="T-REC-X.508-202410-I!!PDF-E",
        sha256="5bc486d7a74eafea9b59beca87e2184f6e46b427d8319776fa28db4916d88996",
        octets=5_269_130,
        note="X.500 catalog sync 2026-11-07: id read off the ITU component page, which lists this PDF as freely "
        "available at 5269130 bytes; digest from the bytes downloaded.",
    ),
    Edition(
        key="X.509#2019-10",
        rec="X.509",
        edition="10/2019",
        title="The Directory: Public-key and attribute certificate frameworks",
        status="in force",
        artifact="T-REC-X.509-201910-I!!PDF-E",
        sha256="1f4ea2939ecc31a3433c499084d485e770f9b8dcee55a0ba9fe4c27128822e8c",
        octets=3_581_573,
        note="X.500 catalog sync 2026-11-07: id read off the ITU component page, which lists this PDF as freely "
        "available at 3581573 bytes; digest from the bytes downloaded.",
    ),
    Edition(
        key="X.510#2023-10",
        rec="X.510",
        edition="10/2023",
        title="The Directory: Protocol specifications for secure operations",
        status="in force",
        artifact="T-REC-X.510-202310-I!!PDF-E",
        sha256="c49f3336cfd6ffbe2e188fc92a9cf3cb1cb83adea5210816d41cae9a390e9dbc",
        octets=2_368_874,
        note="X.500 catalog sync 2026-11-07: id read off the ITU component page, which lists this PDF as freely "
        "available at 2368874 bytes; digest from the bytes downloaded.",
    ),
    Edition(
        key="X.511#2019-10",
        rec="X.511",
        edition="10/2019",
        title="The Directory: Abstract service definition",
        status="in force",
        artifact="T-REC-X.511-201910-I!!PDF-E",
        sha256="fba5830e90c3084b5bae97dce0547507e4cc864bffc0e0e4e6ffab95dab83c63",
        octets=2_253_433,
        note="X.500 catalog sync 2026-11-07: id read off the ITU component page, which lists this PDF as freely "
        "available at 2253433 bytes; digest from the bytes downloaded.",
    ),
    Edition(
        key="X.518#2019-10",
        rec="X.518",
        edition="10/2019",
        title="The Directory: Procedures for distributed operation",
        status="in force",
        artifact="T-REC-X.518-201910-I!!PDF-E",
        sha256="8c3333351bac45f65dd33ed6dbd09e55b173129fff63c5064a699b298e0b608d",
        octets=4_130_297,
        note="X.500 catalog sync 2026-11-07: id read off the ITU component page, which lists this PDF as freely "
        "available at 4130297 bytes; digest from the bytes downloaded.",
    ),
    Edition(
        key="X.519#2019-10",
        rec="X.519",
        edition="10/2019",
        title="The Directory: Protocol specifications",
        status="in force",
        artifact="T-REC-X.519-201910-I!!PDF-E",
        sha256="d09b59636bbbce77aaab3d0e8b23e17c6a1e507a535e65e5a46217175d9ac924",
        octets=1_651_882,
        note="X.500 catalog sync 2026-11-07: id read off the ITU component page, which lists this PDF as freely "
        "available at 1651882 bytes; digest from the bytes downloaded.",
    ),
    Edition(
        key="X.520#2019-10",
        rec="X.520",
        edition="10/2019",
        title="The Directory: Selected attribute types",
        status="in force",
        artifact="T-REC-X.520-201910-I!!PDF-E",
        sha256="78cac8b619e69af06ae0ae9216716d400117152086e85c4ad267efef80bd3fd1",
        octets=2_228_421,
        note="X.500 catalog sync 2026-11-07: id read off the ITU component page, which lists this PDF as freely "
        "available at 2228421 bytes; digest from the bytes downloaded.",
    ),
    Edition(
        key="X.521#2019-10",
        rec="X.521",
        edition="10/2019",
        title="The Directory: Selected object classes",
        status="in force",
        artifact="T-REC-X.521-201910-I!!PDF-E",
        sha256="da551843f975f7d54cb0bef92a3b9cec7efcfdf3177e9d0ce434d9424a7f63e3",
        octets=1_079_233,
        note="X.500 catalog sync 2026-11-07: id read off the ITU component page, which lists this PDF as freely "
        "available at 1079233 bytes; digest from the bytes downloaded.",
    ),
    Edition(
        key="X.525#2019-10",
        rec="X.525",
        edition="10/2019",
        title="The Directory: Replication",
        status="in force",
        artifact="T-REC-X.525-201910-I!!PDF-E",
        sha256="49eedd99ab3892ad85ac46ac70d20548dec7e9ed6043d8a446cf7874e30b5efd",
        octets=1_288_207,
        note="X.500 catalog sync 2026-11-07: id read off the ITU component page, which lists this PDF as freely "
        "available at 1288207 bytes; digest from the bytes downloaded.",
    ),
    Edition(
        key="X.530#2008-11",
        rec="X.530",
        edition="11/2008",
        title="The Directory: Use of systems management for administration of the Directory",
        status="in force",
        artifact="T-REC-X.530-200811-I!!PDF-E",
        sha256="2c6da6878e3f83b427dcd59f8e741a4daaadd8c545bc818d4081b65742520090",
        octets=675_123,
        note="X.500 catalog sync 2026-11-07: id read off the ITU component page, which lists this PDF as freely "
        "available at 675123 bytes; digest from the bytes downloaded.",
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
        key="X.500#2019-10!amd1",
        rec="X.500",
        label="Amendment 1 (10/2024) to Rec. X.500 (2019): Miscellaneous enhancements",
        status="in force",
        artifact="T-REC-X.500-202410-I!Amd1!PDF-E",
        note="X.500 catalog sync 2026-11-07: listed In force on the X.500 page, PDF 218291 bytes as listed. "
        "Not applied to the base text and not indexed; read it with `itulib read X.500#2019-10!amd1`.",
        sha256="df26e76b8cd2e9e17de507f2187f15dc10d11b8894894758eb3eeed7e7b8ec8d",
        octets=218_291,
    ),
    Amendment(
        key="X.501#2019-10!amd1",
        rec="X.501",
        label="Amendment 1 (10/2021) to Rec. X.501 (2019): Miscellaneous enhancements",
        status="in force",
        artifact="T-REC-X.501-202110-I!Amd1!PDF-E",
        note="X.500 catalog sync 2026-11-07: listed In force on the X.501 page, PDF 351086 bytes as listed. "
        "Not applied to the base text and not indexed; read it with `itulib read X.501#2019-10!amd1`.",
        sha256="24ad1e87d3c9eff366cc178616fa88c4b6e9c47ea29504001259337bea6a1bdb",
        octets=351_086,
    ),
    Amendment(
        key="X.501#2019-10!amd2",
        rec="X.501",
        label="Amendment 2 (10/2024) to Rec. X.501 (2019): Miscellaneous enhancements",
        status="in force",
        artifact="T-REC-X.501-202410-I!Amd2!PDF-E",
        note="X.500 catalog sync 2026-11-07: listed In force on the X.501 page, PDF 550429 bytes as listed. "
        "Not applied to the base text and not indexed; read it with `itulib read X.501#2019-10!amd2`.",
        sha256="084fbedc61083c3e5b2a0f6b6c5e44b62f6d1cf0ed1d93bb5ed59ac08fea5872",
        octets=550_429,
    ),
    Amendment(
        key="X.509#2019-10!cor1",
        rec="X.509",
        label="Corrigendum 1 (10/2021) to Rec. X.509 (2019)",
        status="in force",
        artifact="T-REC-X.509-202110-I!Cor1!PDF-E",
        note="X.500 catalog sync 2026-11-07: listed In force on the X.509 page, PDF 367050 bytes as listed. "
        "Not applied to the base text and not indexed; read it with `itulib read X.509#2019-10!cor1`.",
        sha256="ddcc42186f120c51d40ba278b0ca31f528fde851ea663a69474fbcd09bd06f7c",
        octets=367_050,
    ),
    Amendment(
        key="X.509#2019-10!cor2",
        rec="X.509",
        label="Corrigendum 2 (10/2023) to Rec. X.509 (2019)",
        status="in force",
        artifact="T-REC-X.509-202310-I!Cor2!PDF-E",
        note="X.500 catalog sync 2026-11-07: listed In force on the X.509 page, PDF 352052 bytes as listed. "
        "Not applied to the base text and not indexed; read it with `itulib read X.509#2019-10!cor2`.",
        sha256="583416a04fcd76a201e43486d92eb183c5ddae3f03947bf43d50b8185ab5f5a9",
        octets=352_052,
    ),
    Amendment(
        key="X.509#2019-10!amd1",
        rec="X.509",
        label="Amendment 1 (10/2024) to Rec. X.509 (2019): Miscellaneous enhancements",
        status="in force",
        artifact="T-REC-X.509-202410-I!Amd1!PDF-E",
        note="X.500 catalog sync 2026-11-07: listed In force on the X.509 page, PDF 300835 bytes as listed. "
        "Not applied to the base text and not indexed; read it with `itulib read X.509#2019-10!amd1`.",
        sha256="7b0f16ec963fead56accab523fef543295f7946272330b2843799ade96d6cf76",
        octets=300_835,
    ),
    Amendment(
        key="X.511#2019-10!amd1",
        rec="X.511",
        label="Amendment 1 (10/2024) to Rec. X.511 (2019): Miscellaneous enhancements",
        status="in force",
        artifact="T-REC-X.511-202410-I!Amd1!PDF-E",
        note="X.500 catalog sync 2026-11-07: listed In force on the X.511 page, PDF 246331 bytes as listed. "
        "Not applied to the base text and not indexed; read it with `itulib read X.511#2019-10!amd1`.",
        sha256="322169a1f4861f4ca00c49b5c4c7e41686ea3c762d3faa416c9c21888064a806",
        octets=246_331,
    ),
    Amendment(
        key="X.518#2019-10!amd1",
        rec="X.518",
        label="Amendment 1 (10/2024) to Rec. X.518 (2019): Miscellaneous enhancements",
        status="in force",
        artifact="T-REC-X.518-202410-I!Amd1!PDF-E",
        note="X.500 catalog sync 2026-11-07: listed In force on the X.518 page, PDF 239174 bytes as listed. "
        "Not applied to the base text and not indexed; read it with `itulib read X.518#2019-10!amd1`.",
        sha256="312d69f9f4094548ce8f15cee1d43dd42ce5070f2491250a9fb92121e0032ff3",
        octets=239_174,
    ),
    Amendment(
        key="X.519#2019-10!amd1",
        rec="X.519",
        label="Amendment 1 (10/2024) to Rec. X.519 (2019): Miscellaneous enhancements",
        status="in force",
        artifact="T-REC-X.519-202410-I!Amd1!PDF-E",
        note="X.500 catalog sync 2026-11-07: listed In force on the X.519 page, PDF 278528 bytes as listed. "
        "Not applied to the base text and not indexed; read it with `itulib read X.519#2019-10!amd1`.",
        sha256="40d6c66587c395836491589d9dbe0660e349b30e39f79b4ed9b2118859829952",
        octets=278_528,
    ),
    Amendment(
        key="X.520#2019-10!amd1",
        rec="X.520",
        label="Amendment 1 (10/2024) to Rec. X.520 (2019): Miscellaneous enhancements",
        status="in force",
        artifact="T-REC-X.520-202410-I!Amd1!PDF-E",
        note="X.500 catalog sync 2026-11-07: listed In force on the X.520 page, PDF 560983 bytes as listed. "
        "Not applied to the base text and not indexed; read it with `itulib read X.520#2019-10!amd1`.",
        sha256="20ff1efd7cee34887939b73d82bd9f4e32e8ea39d8df2ebc2c9eb1302de7671d",
        octets=560_983,
    ),
    Amendment(
        key="X.521#2019-10!amd1",
        rec="X.521",
        label="Amendment 1 (10/2024) to Rec. X.521 (2019): Miscellaneous enhancements",
        status="in force",
        artifact="T-REC-X.521-202410-I!Amd1!PDF-E",
        note="X.500 catalog sync 2026-11-07: listed In force on the X.521 page, PDF 231439 bytes as listed. "
        "Not applied to the base text and not indexed; read it with `itulib read X.521#2019-10!amd1`.",
        sha256="f78c10f0266c004c6cc5fb822a2cfb758439734aba6977578ab68969d24cd435",
        octets=231_439,
    ),
    Amendment(
        key="X.525#2019-10!amd1",
        rec="X.525",
        label="Amendment 1 (10/2024) to Rec. X.525 (2019): Miscellaneous enhancements",
        status="in force",
        artifact="T-REC-X.525-202410-I!Amd1!PDF-E",
        note="X.500 catalog sync 2026-11-07: listed In force on the X.525 page, PDF 207369 bytes as listed. "
        "Not applied to the base text and not indexed; read it with `itulib read X.525#2019-10!amd1`.",
        sha256="787be5f950b4b3f950326a1bd80ffd36979043918bf41ae35bed65f664c743c8",
        octets=207_369,
    ),
    Amendment(
        key="X.509#2019-10!cor3",
        rec="X.509",
        label="Corrigendum 3 (07/2026) to Rec. X.509 (2019)",
        status="in force (prepublished)",
        artifact=None,
        note="Not registered. The X.509 page lists it 'In force (prepublished)', free download, 492,808 bytes "
        "(id T-REC-X.509-202607-P!Cor3!PDF-E). `dologin_pub.asp` returns an 11,563-byte login page for it; only "
        "`dologin.asp`, the URL on the component page itself, served a %PDF of the listed size. That is not the "
        "URL template this registry uses, and a prepublished text can change before final publication, so "
        "pinning a digest now would pin a draft.",
    ),
    Amendment(
        key="X.510#2023-10!amd1",
        rec="X.510",
        label="Amendment 1 (07/2026) to Rec. X.510 (2023)",
        status="in force (prepublished)",
        artifact=None,
        note="Not registered: the component page restricts it to TIES users (listed 392,348 bytes); "
        "`dologin_pub.asp` and `dologin.asp` both return a login page.",
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

# In-force X.500-series recommendations that could not be registered, with the reason read off ITU's page.
NOT_REGISTERED: dict[str, str] = {
    "X.506": "X.506 (07/26), 'The Directory: General methods for migration of cryptographic algorithms': "
    "In force (prepublished) and 'Document restricted to TIES users' (listed 883,728 bytes); both download URLs "
    "return a login page.",
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
