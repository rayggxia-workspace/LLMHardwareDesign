# Actual C43 final verification

The four distinct implementations in job120292 completed routing with zero reported route violations and zero setup, hold, capacitance, slew and fanout violations. Plan0 is selected because it has the largest actual extracted setup margin: **+0.006340040ns**, hold **+0.001990130ns**, at Nangate45 TT, 250MHz, 0.1ns uncertainty and 50fF on selected outputs. These margins are small. They do not establish A/B top-level extracted-RC timing or other PVT corners.

Selected source: `/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v43-margin-plan0`. Final GDS SHA256: `11ed17a55e077a71217667ae6f7e2bb7dbb07d5af22e52450d159d1de4b0bbe9`. Final netlist SHA256: `2b74fbc9009a57b54f177c89a929a08abfadff7f566ed56928b0ce1441606e77`.

Completed same-source checks:

- 278701 nets have equal pre/post-extraction physical material, including vias; components, pins and special nets are exact. The saved SPEF belongs to the actual checked geometry.
- Independent original-SDC timing/electrical checks, asynchronous controls, both uncached power rails, all153 C BUF_X8 drivers and fixed signal-pin/macro/die geometry pass.
- Actual ODB export is byte equal to the saved final netlist. Job120296 proves the actual final netlist against its qualified synthesis boundary, including21095 states and clock/reset/control cones. Original RTL-to-boundary correctness uses the explicitly recorded finite and generic proofs plus manual compositional bridges; whole-module RTL SAT and four-state equivalence are not claimed.
- Focused upper-metal and antenna checks pass. The fresh native checker has222 individually explained single-net M2/M3 spacing markers; its report is not empty. Final root disposition must additionally bind the complete original-deck result for this exact GDS.
- PG boundary checks pass. The current power boundary is equal to the qualified v16/C35 baseline; versus original CTS,230 power BPin records are removed and140 added. Signal pins remain exact.
- Liberty, physical LEF and parent abstract import and coverage checks pass. The exact accepted G hold03-v3 leaf views are bound to the actual C configuration.
- Independent A/B coverage is340/340 unique BUF_X8 outputs: C153/U153/G33/S1; A uses306 and B340. P is excluded.

**C is not yet accepted.** Job120303 is running the complete unchanged original FreePDK45 deck on this same final GDS. Original deck SHA256: `4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147`. Final acceptance requires its actual zero-item report, root exact native/PG disposition, strict final aggregation and frozen release. No source artifact may be changed during these checks.

Evidence: [final actual proof](C43-plan0-final-proof/proof/complete-equivalence-receipt.json), [340-port coverage](final-340-coverage-v1.json), [source proof semantics](C-final-source-chain-semantic-verification.json), and [preflight evidence](C43-pending-evidence/pending-index.json). Preflight is explicitly not acceptance. U/G/S/F accepted packages remain frozen.
