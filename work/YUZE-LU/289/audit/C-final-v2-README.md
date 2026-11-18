Final C proof v2
================

This version preserves all v1 scripts, run manifests, and failures. It uses the shared frozen `C-fixture-catalog-v2.json` (SHA256 `b8c47e99669b7c9069ad9369301d406ef788af3b0abd78e297bf2a2765bfc963`). The catalog maps 97 standard-cell masters to original full-deck fixture receipts, including the original 34, four additional cells, five memwr cells, AOI221_X4, two trace cells, 50 original standard cells, and six fill cells. Duplicate coverage is retained. OAI221_X4 is excluded.

The source manifest requires absolute `gate`, `config`, `odb`, `provenance`, and `fixture_catalog` paths, all present in `expected_sha256`. Include the CU frozen edit/route/choice dependencies there too. The catalog is independently verified against every recorded source hash before any proof; all catalog sources are bound again before and after proof. A lexical master inventory catches missing fixtures early, followed by the authoritative Yosys physical-JSON inventory check.

Use `sbatch c-final-v2.sbatch /absolute/source-manifest.json /absolute/new-proof-directory`. The gold remains the exact actual C-v16 synthesis. Data/state/macro and independent clock/reset/control proofs must both pass, with exactly 21095 states and the previously admitted FF sizing changes. This is a full proof for the specified candidate, not inheritance of a previous candidate's interface.

For a routed candidate, first fresh-export Verilog from its frozen actual ODB and bind the ODB/exporter/log/model configuration and output. A subsequent route-only modification can reuse the proof only when the independently reviewed fresh export is byte-identical; otherwise reprove. Fixture checks do not replace parent DRC, antenna, power connectivity, RCX material correspondence, or STA.

Catalog qualification ran as 120270. Initial 120269 stopped because an old export receipt recorded relative `export.py`; resolving that path against its fixture directory fixed the catalog reader. No old fixture or receipt changed.
