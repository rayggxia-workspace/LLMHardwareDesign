# W8A16 physical preparation — Refs #250

This directory pins the actual main evidence at `c4d7b960599b9d292f27eb4429d5f226a7156c95`, reconstructs compact area/native pin baselines and provides source-bound G implementation gates. The initial baseline is preparation; the later [P-only G32 result](../../../work/YUZE-LU/250/physical/G32_RESULTS.md) has its own complete native-leaf and finite-access evidence. The declaration preflight below never qualifies a physical implementation. No control grouping becomes a large hard Block.

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

The G32 backend scripts are `g_map.py`, `g_route.py`, `g_audit.py`, `g_function.py` and `g_formal.py`; `stage_backend.py` snapshots committed sources into fresh issue250-only Slurm directories and `harvest_backend.py` retrieves bounded exact-byte receipts/logs. Original Liberty and full FreePDK45 deck SHA-256 values are asserted by `native.py`. The frozen container's default persistent ABC reader stalled after producing its result; `abc_batch.py` transparently forwards the exact generated script through Yosys's explicit batch `-exe` transport, with the original ABC binary and DEVNULL stdin. Both transport failures and the 34-second successful batch mapping remain recorded.

`g_pins.py` supplies a compact edge-staggered placement callback to the unchanged generic main physical engine. It preserves the 204 native bits, 2×2 µm M10 pins, 4 µm tracks, 2.2 µm cut spacing and the full original geometric checker. It places stagger bands near 12/16 µm from the four edges rather than at quarter-width positions. A 240 µm candidate fits 51 pins per side. This changes actual endpoint placement, not rules or interface widths; actual native PG/DRC, final ODB pin equality and physical escape gates remain necessary. Final density is measured from the final ODB, with both corresponding main G occupied/outline and occupied/core floors; mapped area, filler and antenna cells cannot make this gate pass.
