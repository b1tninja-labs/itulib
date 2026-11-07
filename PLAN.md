# itulib: the ITU-T corpus, citable by clause

The encoding rules are not in the RFC series. `asn1core/AGENTS.md` says so, `asn1core/VECTORS.md` says so, and
`rfclib` cannot answer a question about high-tag-number minimality or DER ordering no matter how it is asked.
This repository is the same shape of tool pointed at the other corpus: clause-precise search, one-clause reads,
an errata surface, and an MCP server, so the answer to "what does X.690 actually say" is a tool call with a
citation attached rather than somebody's recollection.

Name: `itulib`, measured free on PyPI with `sdk-forge/names.py`. Repo `itulibrary`, package `itulib`,
mirroring `rfclibrary`/`rfclib`.

## 1. Authoritative sources (all of this was fetched, none of it recalled)

Landing pages: <https://www.itu.int/rec/T-REC-X.690/en> and <https://www.itu.int/rec/T-REC-X.680/en>.

| Document | In force | Joint designation | Download (measured working) | What arrived |
|---|---|---|---|---|
| X.690 | **02/2021** | ISO/IEC 8825-1:2021 | `dologin_pub.asp?id=T-REC-X.690-202102-I!!PDF-E&type=items` | PDF, 840,764 B, sha256 `6ac799a2…bd6c`, 38 pages, 98,873 chars extract |
| X.680 | **02/2021** | ISO/IEC 8824-1:2021 | `…T-REC-X.680-202102-I!!PDF-E…` | PDF, 2,088,934 B, sha256 `b69dc475…ee14` |

X.690 lineage from the ITU page: 07/94 → 12/97 → 07/02 → 11/08 → 08/15 → **02/21**, with Amendment 1 (06/99)
"Relative object identifiers", Amendment 1 (10/03) "Support for EXTENDED-XER", **Amendment 2 (06/06) "Time type
support"**, and Corrigenda 05/07, 10/11, 03/14. Two 1997-era corrigenda are marked "Never published". X.680
(2015) carries Corrigenda 1–3 and Amendment 1 (05/18).

**ITU publishes errata.** The X.690 page lists *X.690 (2021) Erratum 1 (09/21) to Rec. X.690 (2021) |
ISO/IEC 8825-1:2021* as **In force** — the analogue of `rfclib.errata`, which is why `itu_errata` exists. The
download id was the open problem when this plan was written: the obvious `!!ERSN1-E` and `!!DOC-E` artefacts
return **HTTP 500**. It has since been read off the erratum's own page (`T-REC-X.690-202109-I!Err1!PDF-E`),
fetched and pinned (ROADMAP.md `ia.erratum_artefact_ids`). The collective X.680–X.693 Word archive still
redirects to a `choice_pub.asp` interstitial that returns HTML, and is not used.

The table above is the first two editions measured. The registry now holds all twelve X.680-X.697 recommendations
in their 02/2021 editions plus the superseded X.690 11/2008 and 08/2015 base texts, each with a pinned digest
(`itulib/sources.py`; ROADMAP.md `ia.catalog_asn1`, `ia.superseded_editions`).

## 2. The licence decides the architecture

Page iii of X.690 (02/2021) carries ITU's notice: all rights reserved, and no part of the publication may be
reproduced by any means without ITU's prior written permission. Paraphrased here on purpose —
`tests/test_license.py` fails if the sentence itself ever appears in this tree.

That is the one respect in which this cannot be a clone of `rfclibrary`. The RFC series is freely
redistributable, so `rfclibrary` vendors `data/` and a clone is self-contained. ITU text may not be vendored:

- the corpus is **fetched by the user** (`itulib fetch`) into `ITULIB_HOME` (default `~/.itulib`),
  never into the checkout;
- `corpus/` is git-ignored; `tests/test_license.py` forbids PDF/DOC/ZIP blobs, forbids five verbatim clause
  sentences anywhere in the tree, and forbids any test from requiring the corpus, because a suite that skips
  quietly reports the same green as one that ran;
- digests are **pinned in `sources.py` from bytes actually downloaded**, and `fetch` refuses a mismatch saying
  ITU may have republished the edition.


## 3. The backlog this exists to retire

`VECTORS.md` marked a row `[verify against X.690]` when the rule was written from knowledge of the encoding
rules rather than from the text, and line 106 records the price: an earlier `oid-first-arc-high` row asserted
that arc 3 was illegal, and **that was wrong**. The backlog is now retired: asn1core commit `0fc1e5f`
(2026-11-06) attached an edition and subclause to all nine markers, and `VECTORS.md` line 253 records them as
resolved. Each row was queried against the fetched 02/2021 text and re-read with `itulib read` on 2026-11-06;
the rules below are paraphrased, and the citation is the authority rather than this table.

| Row | Clause in X.690 (02/2021) | Status |
|---|---|---|
| `tag-nonminimal` (`9F 80 01 00`) | §8.1.2.4.2 c), high-tag-number identifier octets | **resolved**: the minimality rule the row needs is stated there |
| `len-nonminimal` | §10.1, with §8.1.3 for the BER length forms | **resolved**: DER lengths are definite and minimal, so 127 in long form is refused |
| `len-indefinite` (primitive) | §8.1.3.2 a) | **resolved**: a primitive encoding always takes the definite form, so primitive-with-indefinite-length is never conforming |
| `len-undefined-high` | §8.1.3, length octets | not one of the nine markers; `VECTORS.md` gives it no clause yet |
| `int-nonmin` (`02 02 00 01`) | §8.3.2, integer encoding | **resolved**: minimality is stated, with a NOTE giving its purpose |
| `bool-nonzero` (`01 01 02`) | §8.2.2 against **§11.1** | **resolved**: BER permits any non-zero contents octet for TRUE; §11.1 narrows it to an all-ones octet under CER and DER |
| `setof-unsorted` | **§11.6**, with §8.10.3 for the SEQUENCE OF contrast and §9.3/§10.3 for `SET` | **resolved, and the row understates it**: DER orders the component encodings of a `SET OF` by comparing them as octet strings, padding the shorter with zero octets for the comparison only — the padding is never emitted. `SET` (not `OF`) components are ordered by tag under §9.3/§10.3, a different rule the row does not distinguish |
| `time-leap-second` (`"500101000060Z"`) | §11.7 GeneralizedTime, §11.8 UTCTime | **re-pointed**: X.690 fixes the form and defers the alphabet to X.680 \| ISO/IEC 8824-1. Nothing in X.690 addresses a seconds value of 60 — searched, no match — so the marker belongs on X.680, where §47.3 bounds UTCTime seconds at 00 to 59: `60` is an ill-formed value |
| `oid-first-arc-high` (`06 02 7F 01`) | §8.19.4 | **resolved**: the first subidentifier packs the first two components as `(X*40) + Y`, and the NOTE limits 0 to 39 to the nodes under X = 0 and X = 1, so `0x7F` is `2.47` and the old "illegal" row was wrong |
| `printable-charset` | X.680 §41.4, Table 10 | **resolved** (X.680 side): the PrintableString alphabet is listed there |

## 4. Boundaries

- **`rfclib` stays the authority for the RFC side.** RFC 5280 §4.1.2.5.1 constrains certificate time fields and
  is an RFC; X.690 constrains the encoding and is not. Each question goes to the tool that owns its corpus.
- **Not a validator.** itulib answers what a clause says; `asn1core` decides what to accept, and `VECTORS.md`
  stays the exit test.
- **Not a conformance oracle.** An unresolved marker stays unresolved. The codec must not code against an
  invented interpretation, which is why `test_defect_corpus.py` refuses primitive indefinite length.
- X.680-X.697 are all registered now, and so is the X.500 family (X.500, X.501, X.508-X.511, X.518-X.521, X.525,
  X.530) as of 2026-11-07; see `ia.catalog_x500`. Scope grows beyond them (jointly ISO/IEC 9594-8 for X.509)
  only as questions arrive.

## 5. Exit test

`itulib read X.690 11.1` answers on a machine that ran `fetch`; `python -m pytest` passes on one that has not;
and every `[verify against X.690]` marker in `asn1core/VECTORS.md` is either retired with an
edition-and-clause citation or re-pointed at the document that actually carries the rule.

