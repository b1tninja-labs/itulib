# itulib

ITU-T recommendations as a local, citation-precise library and MCP server. **X.680 and X.690 first** — the
normative source for ASN.1 and the DER/BER/CER encoding rules, which are not in the RFC series and so are out
of reach for [`rfclib`](../rfclibrary/).

```
python -m itulib.cli fetch X.690     # downloads to ~/.itulib (or $ITULIB_HOME). Never into this repo.
python -m itulib.cli index X.690
python -m itulib.cli read  X.690 11.1
```

The corpus is fetched by you and is never distributed with this package: ITU reserves all rights in the text of
its recommendations. A clone of this repository contains code, a pinned edition registry and tests that pass
with no corpus present — see `PLAN.md` §2 and `tests/test_license.py`.

| | |
|---|---|
| Why it exists | `asn1core/VECTORS.md` carries rules marked `[verify against X.690]`, and one such remembered rule (an illegal OID arc) was wrong |
| Citation shape | `Rec. ITU-T X.690 (02/2021) §11.1` |
| Tools | `itu_info` · `itu_search` · `itu_read` · `itu_outline` · `itu_grep` · `itu_errata` |
| Plan | `PLAN.md` — sources, licence, and the marker backlog with its current status |
| Rules | `AGENTS.md` — two of them, and both are load-bearing |
