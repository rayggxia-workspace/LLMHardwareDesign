# Main compact physical baseline and backend preparation

Refs [#250](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/250). Source main: `c4d7b960599b9d292f27eb4429d5f226a7156c95`. Branch: `task/250-compact-physical-baseline`. This is an independent-leaf baseline and a preparation gate. New W8A16 M/G, new feeders, shared memory and the full product have **not** inherited these leaves' acceptance.

## Measured main baseline

All areas are µm². Occupied area means functional standard cells plus embedded hard-macro outlines, excluding filler/tap/endcap/antenna. Values below are rounded for reading; the executable [baseline](../../../../project/experiments/w8a16_physical/baseline.json) stores the exact calculations.

| Native leaf | Outline µm | Core area | Functional cells | Embedded bank outlines | Occupied / outline | Occupied / core | Native signal bits | TT setup / hold ps |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| M | 930×930 | 791,005.530 | 304,336.186 | 0 | 35.19% | 38.47% | 867 | +39.857 / +18.500 |
| compact G | 220×220 | 36,806.420 | 22,814.022 | 0 | 47.14% | 61.98% | 108 | +540.702 / +19.851 |
| compact E | 340×340 | 94,371.480 | 63,981.778 | 0 | 55.35% | 67.80% | 273 | +360.072 / +19.880 |
| S_base | 880×520 | 439,861.856 | 7,441.616 | 369,848.2001 | 82.45% | 85.77% | 273 | +158.919 / +33.924 |
| S_P | 900×540 | 462,700.084 | 29,210.258 | 369,848.2001 | 82.11% | 86.25% | 965 | +324.828 / +8.592 |

M's delivery `active_area_um2=304530.898` includes 194.712 µm² of pure antenna cells. G/E delivery area similarly includes 19.152/37.506 µm² of antenna cells. The compact occupancy reports exclude these; the new density comparison uses the same exclusion everywhere. M's synthesis mapped area 261,780.708 is not its routed cell area. Padding with filler cannot satisfy the density gate. The tighter S_P 880×528 candidate reached 85.84% but failed hold and maximum capacitance; it is not an accepted replacement.

Each S contains four actual 256×128-bit 1RW banks = 16 KiB usable and 16 KiB physically instantiated. Bank footprints occupy 80.82% of S_base and 76.10% of S_P. A top-level P grouping that instantiates M, G and S_P has 1,399,300 µm² of **leaf outlines**, before its own controller/adapter cells, halos and channels. Its 726,208.6661 µm² of internal useful area is a separate statistic and must not be added again to those outlines. No rectangular P/U/C/F/J boundary is required by this accounting.

## Actual S_P interface and timing facts

Pinned source: `project/rtl/s_sram/local_s_p.sv`, `block_feed_s16k_sram.sv`, and `project/rtl/block_feed_v1/block_feed_loader.sv` in the source main commit.

- The ordinary native request/response port is 128 bits (16 B), address 10 bits. Word address bits `[1:0]` choose a bank and `[9:2]` choose a row. There are two reserved response slots including in-flight work. Replies retire in order. Write ACK follows the actual SRAM write phase; write response data is zero.
- Internally, a wide read selects **all four banks at the same row**, producing 512 bits. The SRAM path samples the command at rising edge K, completes in the low phase and registers the response at rising edge K+1. It can reserve back-to-back reads when its consumer permits. This internal path is not an exposed 64 B ordinary port.
- The actual exposed feeder sends A **128 bits** and B **512 bits**. `load_a_wide` is a format tag, not a wider A bus. Four 128-bit A containers are selected from one 512-bit queue entry. The current feeder permits only one wide read outstanding, and only issues a successor when the previous response is consumed. Its exact service cadence must be traced rather than modelled as a free 64 B/cycle shared calendar.
- The ordinary port and feeder are mutually exclusive phases. A new feeder job waits until ordinary requests retire; a normal phase waits for feeder work and its done event to retire. When both new requests arrive idle, feeder wins. Writes, ordinary reads, feeder reads and compute overlap must follow this actual contract.
- An A16 K16 vector is 32 B. Supplying one such vector in one cycle needs a changed A interface/loader or an explicit wide-read adapter; two 16 B A beats do not become one 32 B physical beat by changing a model parameter. Retaining 16 KiB of banks is possible, but new active logic, buffers, pins and read/write arbitration require new measurement and acceptance.

## Native pins, escape, halos and PG

S_P has 965 signal bits: 273 ordinary bits, 33 feeder-command bits, 3 completion bits, 137 A bits and 519 B bits. VDD/VSS are separate. Macro-native M10 pins are retained; no control grouping creates another set of payload pins on a large artificial Block frame.

The compact S pin CSVs are from final DEF readback. S_P top/bottom macro bands are roughly 12/72/124 µm from the edge; west/east 12/40/68 µm. Each band keeps the old 4 µm local staggering. Every signal has a separate escape track on its side/layer. S_P uses two upper layers including short nonpreferred segments; S_base needs preferred directions only. G/E use their selected two-band pin plans. All five baselines have finite simultaneous M11/M12 escape evidence with KLayout readback, not permission to route arbitrary long product wires at the same load.

Pin/escape entry points are `block_v1/pin_contract.py`, `block_v1/io_slots.py`, `compact_local_s/pins.py`, `block_v2/compact_release.py` and the exact-view `pu_leaf_base/physical.py`/`leaf_access.tcl` flow. New native port widths must first reproduce every declared signal bit in exact M10 DBU rectangles, avoid native PG/obstacles, pass all-pin simultaneous access, and then pass the real product route/load/RC checks. M11/M12 rules here are the project's explicit 2 µm research rules; independent escape is not foundry tapeout qualification.

The existing independent-leaf P/U integration coupon uses 48 µm outer margins, trial gaps 48/88/136/200 µm, `MACRO_PLACE_HALO=12 12`, tap-cell halo 4 µm and macro PDN halo 2 µm. These are **recorded candidate settings**, not a global fixed whitespace allowance. The compact S bank placements use smaller measured internal gaps and row cuts. New placement should reuse exact native obstruction geometry, preserve bank/PG halos, inspect signal access and tighten gaps when actual geometry permits.

The parent PDN coupon uses M1 followpins (0.17 µm/2.4 µm pitch), M4 (0.48/56), M7 (1.40/30), M10 (1.40/60); PG offsets are trialled. Native macro grid obstructions and supply landing cuts remain present. Global VDD/VSS attachment, zero incorrect/open PG terminals and native `check_power_grid` are required. A removed route obstruction or cropped GDS is not a density fix.

## Reusable backend and dependency inventory

The read-only remote recovery changed no old directories and submitted no EDA job. [evidence/index.json](evidence/index.json) records exact remote paths, byte sizes and SHA-256 for 14 small reports. M's two newly recovered JSONs also match hashes already committed in the main six-leaf bundle. The G/E delivery binds each compact occupancy report; S audits bind the same final ODB/DEF/V/SDC/SPEF/GDS as the selected candidate receipts.

| Purpose | Existing executable/source | Exact reusable dependency or evidence |
| --- | --- | --- |
| Compact SRAM synthesis/route | `project/experiments/compact_local_s/physical.py`, `worker.sh` | `issue-200-compact-local-s/run08-base0/results/0` and `run10-delay1/results/4` |
| SRAM independent audit | `compact_local_s/audit.py`, `audit.sh`, `clock_checks.py` | `audit08/base0`, `final-gates/p-audit`; selected S_P uses cap margin35, hold repair target0.008 ns, one feeder input buffer stage; original timing/electrical limits remain unchanged |
| Native G/E route and audit | `block_v2/physical.py`, `remote_compact_ge*.sh`, `qualify.py` | compact G220 bands2 and E340 bands2 source folders recorded in delivery JSON |
| Complete release | `block_v2/compact_release.py`, `deliver.py` | require same-source independent physical, DRC, final-netlist three-initial-state function, strict boundary LEC before packaging |
| Useful density | `block_v2/compact_occupancy.tcl`, `.py`; `compact_local_s/inventory.tcl`, `occupancy.py` | exact functional/physical-only separation; 10 µm connected-empty-grid for G/E and 16×10 fractional grid for S are different metrics |
| Independent-leaf placement | `pu_leaf_base/physical.py`, `physical.sh` | compact G/E release and compact S accepted views; exact native obstruction and PG access controls |
| Actual SRAM bank | `issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45*` | physical.py pins RTL/Liberty/LEF/GDS SHA; TT1.1V25C characterization scope remains #158/#186 |
| Tool container | `/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif` | source `/OpenROAD-flow-scripts/env.sh`; use original Nangate45 typical Liberty, RCX rules, GDS map and full FreePDK45 rule deck |
| RTL trace/regression | `compact_local_s/simulate.sh` | Verilator `/public/home/yuzelu/opt/eda/verilator-5-042-repro02/bin/verilator`, real OpenRAM model; preserve three initial states for final-netlist acceptance |

Remote evidence root is `/public/home/yuzelu/project-circuit/LLMHardwareDesign/` except the explicitly indexed historical M delivery. New work must stay under an issue250-owned fresh root, freeze a source snapshot, preserve all failure/cancelled cases, and use `yzl-*` Slurm names with actual CPU affinity checks. c96 may run eight 12-core tasks and c64 six 10-core tasks within the allocation. No long simulation or P&R runs on login nodes. The tools above are source entry points, not an assertion that an arbitrary new top already works unchanged.

## New P-only G32 result

After the original preparation baseline, the P-only G32 leaf completed the full source-bound native TT300MHz M1–M10 gates and all-204-bit finite escape. The actual final G is 240×240 µm, with 28,461.734 µm² useful standard-cell area, 49.412733% occupied/outline, 66.145125% occupied/core, setup +81.264 ps, hold +19.733 ps and zero original full native GDS DRC items. Actual final-ODB nine-case model-tensor replay and strict all-boundary LEC also pass. See [G32_RESULTS.md](G32_RESULTS.md) and [g32-results.json](g32-results.json) for exact scopes, paths and SHA bindings.

The separate G–S128 frontend has 96 B payload holds plus control/metadata registers, no new SRAM, 107 measured cycles from first request through final ACK for 128 values, and 7,506.254 µm² mapped gate area. It is not physically or integrated-LC qualified. Pure-G 68-cycle arithmetic and full S128 service remain separate quantities. Native G leaf acceptance does not transfer to this frontend or to a product upper-metal route.

## Execution gates for the remaining new hardware

1. Joint numerical/performance result selects a resource candidate; no unmeasured A32/64 B feeder assumption is frozen.
2. New M/G/feeder RTL and reference math agree; backpressure, write ACK, reset, finite contexts and two-lane ROM service are explicit. Report synthesized storage copies, bits, arithmetic and active cell area.
3. Generate native pin inventory and simultaneous finite escape. Compare actual occupied/outline **and** occupied/core against the corresponding main baseline. Record absolute outline, connected empty areas, hard-macro fraction, halos, PG and congestion separately.
4. Run source-bound fresh M1–M10 P&R; preserve failed candidates and modify RTL/pins/placement/repair parameters until original 300 MHz TT setup/hold, max cap/slew/fanout, native connectivity/PG, OpenROAD DRC and original complete native GDS DRC all pass. Do not loosen SDC, Liberty or rule decks.
5. Run final ODB netlist in all three declared initial states, strict real-bank boundary equivalence where applicable, exact pin readback and release SHA checks. Product M11/M12 routes and full-system timing/function remain additional gates.

Initial preparation checks: `scripts/check_project.py` passed; baseline reproduction passed; five focused preflight tests passed. That preparation commit ran no new P&R; the later G result above is separately evidenced. Product routing and the other new macro/control implementations remain separate. Root owns shared project/Issue/progress updates and integration; this branch modifies only the parent-assigned physical/G/frontend paths.
