# Issue93 evidence

Initial `cost01.json` has a known wire-byte accounting error: it treated each actual128bit bridge beat as32bits. The final receipt is `final/cost02.json`; use only the final index/byte/source receipts. Initial artifacts are retained for audit, not current cost conclusions. Actual RTL outputs, cycles, input SHA and mapped inventory were unaffected. See protocol/report erratum.
