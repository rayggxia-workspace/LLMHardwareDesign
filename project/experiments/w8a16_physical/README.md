# W8A16 physical preparation — Refs #250

This directory provides executable **preparation**, not a new accepted macro. It pins the actual main evidence at `c4d7b960599b9d292f27eb4429d5f226a7156c95`, reconstructs the compact area and native pin baselines, and guards resource accounting before candidate P&R. It does not change production RTL or the physical ownership of any Block.

```powershell
python project/experiments/w8a16_physical/baseline.py --check
python -m unittest discover -s project/experiments/w8a16_physical -p test_preflight.py -v
python project/experiments/w8a16_physical/preflight.py --candidate candidate.json
```

`baseline.py` makes no network or EDA call. It reads pinned main blobs using Git and verifies 14 small source-bound remote reports copied under `work/YUZE-LU/250/physical/evidence`. `--output` can regenerate a candidate baseline for comparison. Never overwrite the committed baseline just because a check fails.

`preflight.py` checks a declaration's area arithmetic, density, native RTL pin count and explicitly priced storage. Passing is **not** a physical qualification. It emits `physical_qualified=false` unconditionally. A declaration has `baseline_class` (`M`, `G`, `E`, `S_base`, `S_P`), an `area` object with the five separately measured area terms and the compact exclusion policy, `pins.rtl_ports` as native `{name,width}` entries, actual final ODB signal bits and evidence flags, and a `storage` list with usable bytes, physical bytes, implementation and conflict policy. Tests contain an illustrative in-memory declaration, not a delivered design.

The corresponding main class sets minimum occupied/outline and occupied/core ratios. The old 80% G/E objective was not achieved and is not used as a fabricated accepted metric. Changing functionality can change the macro dimensions; an enlarged but equally dense G is not rejected simply for exceeding the old 220 µm frame. Absolute area, density, pin geometry and final timing remain separate results.

The reproducible byte arithmetic is in `storage-options.json`. `preflight.py --ledger <path>` regenerates it. The 8,128 B budget retains the old 1,024 B Mid allocation; 7,616 B also narrows Mid. These are logical allocations. Neither result shrinks four physical 4 KiB SRAM banks. The new 4×1,152 B weight storage must explicitly replace the old double-B allocation or be charged as additional hardware. G's 257×32 table is 1,028 logical bytes; simultaneous lane lookups, interpolators and multipliers must be priced from the actual implementation.

See [backend readiness](../../../work/YUZE-LU/250/physical/README.md) for native pin, feeder, PG, halo, tool and acceptance boundaries. Candidate macro work begins after the joint numerical/performance gate; independent routed 300 MHz, original full GDS DRC, electrical, actual pin access and density gates remain mandatory. Failed candidates and their original logs stay in their own output directories.
