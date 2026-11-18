Final C proof preparation
=========================

No EDA job is submitted by preparing these scripts. Wait for CU to freeze the exact candidate.

Create a JSON source manifest with absolute `gate`, `config`, `odb`, and `provenance` paths. `expected_sha256` must include those four files and all source/physical choice/frozen edit dependencies supplied by CU. `fixture_receipts` lists original full-deck, translation-only cell fixture receipts (each requires `passed: true`, `count: 0`, and `masters`). Supply real reviewed hashes; no placeholder may be accepted.

Submit `sbatch c-final-v1.sbatch /absolute/source-manifest.json /absolute/new-proof-directory`. The output directory must not already exist. Eight allocated CPUs run the unchanged strict data/state proof followed by the independent tagged, packed clock/reset/control proof. The original actual C-v16 synthesis SHA is fixed. All inputs are hashed before and after; 21095 actual states and exactly the previously admitted FF drive changes are required. Every actual standard-cell master is inventoried, Boolean functions are enumerated from real Liberty, and missing physical fixture coverage stops acceptance while retaining completed proof evidence. Macro semantics remain bound by the original accepted leaf proofs and matching complete macro boundaries.

An after-route candidate may inherit the exact proof only if a fresh ODB-exported logical Verilog is byte-identical to the proved gate (and final ODB, exporter, models, and output are frozen in a separate receipt). Interface, instance counts, or nominal master families are not sufficient. If bytes differ, run this strict proof again on that actual final export. Functional equivalence does not assert DRC, antenna, RCX material, or STA acceptance.
