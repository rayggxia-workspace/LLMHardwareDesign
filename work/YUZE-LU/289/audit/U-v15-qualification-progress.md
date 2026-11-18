# U v15 f67/h3/u1.2 independent qualification — 2026-11-18

Candidate remains pending final aggregation. No source candidate files were edited.

- Frozen diagnostic copy: `audit/U-v15-pg-diagnostic`; original saved ODB/DEF/V/SDC/SPEF from `cu/runs/U-v15-guardant-f67-h3-u1.2`. GDS was streamed from that exact saved DEF and original config under job119765. SHA f66f96a1c89d761c8ad8e139922f445fa760b19ed689d073306e0ac8c22d66ee.
- 119771: upper-spacing diagnostic0, exact foundry antenna diagnostic0. This is not complete deck acceptance.
- 119772: unchanged complete original FreePDK45 deck ongoing.
- 119781: independent fresh STA counts setup/hold/capacitance/slew/fanout all0; slack +0.077999607ns/+0.003471112ns. 153 selected outputs checked >=X8. Original signal pin/die/macro geometry exact; original PG rectangle contract delta172removed/105added. Formal/control still ongoing.
- 119782: staged timing model and zero-bloat LEF export/import ongoing. Current SPEF remains provisionally bound until parent independent re-extraction audit concludes.

## Reported PSM short versus actual saved geometry

119777 independently parses actual net90 DEF wire segments and real via enclosures and intersects them with the merged GDS M1 layer. Within x30–130um/y44.4–45um, every reconstructed net90 M1 rectangle is present in GDS (missing area0). Net90 M1 occupies y44.555–44.625um or44.415–44.485um. Its intersection with the reported rail band y44.715–44.790um is0; actual GDS contains7.5um² M1 in that100um×.075um band. Net90 is separated from that band by at least90nm.

Evidence: `audit/U-v15-pg-diagnostic/net90-m1-physical.json`, bound to exact DEF/GDS SHA. This proves the reported saved physical short strip is not net90 M1; it does not replace complete DRC or extraction verification.

Root119764 and CU119766 also independently read unchanged saved ODB and obtain both PG rails connected. Root is checking RCX normalization and post-extraction geometry to resolve why the original single-process RCX→PSM sequence reports a short. No PG check has been waived, and no full-deck rule changed.
