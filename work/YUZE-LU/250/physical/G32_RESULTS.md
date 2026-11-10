# P-only G32 and finite S128 frontend — Refs #250

The new `P:G32_SILU` leaf has passed the complete independent native TT 1.1 V, 25 °C, 300 MHz M1–M10 gates. The separate 96 B G–S128 frontend has passed native-bank RTL tests and standalone gate mapping; it has **not** received integrated LC or physical qualification. C/F retain `G16_MULTI`; the new P profile does not silently replace their four-function S16 services.

| Final native G32 measurement | Result | Corresponding accepted main G16 baseline |
| --- | ---: | ---: |
| Outline | 240 × 240 µm | 220 × 220 µm |
| Functional standard-cell area, excluding antenna/filler/tap/endcap | 28,461.734 µm² | 22,814.022 µm² |
| Functional area / outline | 49.412733% | 47.136409% |
| Functional area / actual core | 66.145125% | 61.983812% |
| Largest connected empty full 10 µm tiles | 0 µm² | 0 µm² |
| Worst setup / hold | +81.264 / +19.733 ps | +540.702 / +19.851 ps |
| Full original native GDS DRC | 0 | 0 |
| Native signal/clock bits | 204 | 108 |

Absolute area increased because the new arithmetic/format/interface differs. The logical small table does not prove a smaller whole macro. Both final density floors are measured from the actual final ODB; filler, protection cells and mapped-only area cannot satisfy them.

The numerical service is LUT257 Q16 SiLU with adjacent-point RNE13 interpolation and, in gated mode, a 32×32 product followed by RNE16 to stored Mid S32/Q16. There are two lanes and **four** adjacent-point lookup calls per cycle. Yosys initially represents these as four 512×32 read views; the mapped implementation is Boolean standard cells with no SRAM instance. Its 1,028 B logical constant definition is not a promise of one physical table with free read ports. The total mapped G area was 26,301.548 µm²; real repair/CTS/route cells are included in the larger final active area.

The native G pin candidate uses four edge-staggered bands, retaining 2×2 µm M10 pins, 4 µm tracks, 2.2 µm cut spacing and every original 2 µm research rule. All 204 **actual** final M10 bits simultaneously escape through 204 via10 and 102 via11 contacts. Complete native geometry includes wires, PG, master/block OBS and every DEF RECT; three actual DEF/ODB readbacks and independent joined native GDS pass. Native M10 same-net intersections are 409 and obstruction intersections zero. The charged finite test is **320×320 µm**, including 40 µm external halo. This establishes finite research geometry; calibrated upper-metal RC, combined upper-route 300 MHz timing, arbitrary product routing, hierarchical Liberty and manufacturing qualification remain false.

| Exact-source gate | Job | Evidence |
| --- | --- | --- |
| Production strict RTL / actual model arithmetic | 102078 | [G RTL results](g-sim-05/results/summary.json) |
| Fresh original-Liberty batch mapping | 102088 | [mapping receipt](g-map-03/evidence/mapping/g_s32/receipt.json) |
| Fresh native six-stage P&R | 102095 | [route submission](g-route-01/submission.json); producer remains indexed on the authorized project store |
| Independent STA/electrical/RC/PG/pins, density and full original GDS DRC | 102102 | [audit](g-audit-01/evidence/audit/audit-summary.json) |
| Actual final ODB signal-bearing netlist, protection loads retained | 102103 | [final function](g-function-01/evidence/function/final-function.json) |
| Strict all-boundary LEC and actual positive/negative controls | 102105 | [formal](g-formal-01/evidence/formal/formal.json) |
| Same-source native six-file release | 102111 | [delivery](g-deliver-01/evidence/delivery/delivery.json) |
| Actual full-interface DEF/ODB/joined-GDS access | 102113 | [access](g-access-02/evidence/tasks/access/access.json) |

Pure-G RTL and final-ODB tests each replay 8,048 oracle packets in nine traffic/initial-state cases, including 2,048 two-lane packets from four historical actual FFNs: 4,096 model values. The old LUT2049 S64 products are independently reconstructed before computing new LUT257/RNE16 expectations. This is exact tensor replay, not a newly executed complete model or complete FFN. [Source provenance](../../../../project/experiments/w8a16_g/reference_source/model-provenance.json) preserves exact historical bytes and execution source.

The pure kernel accepts a new two-lane packet each cycle. The full 128-value frame occupies 68 inclusive input/output-handshake cycles, with four edges from acceptance to consumption. Final Mid32 RNE is already included; old `NV_MID1` must not be added again. Mid-to-Down A16 group maximum/normalization and actual memory service are separate.

## Finite G–S128 service

`g_s128_frontend.sv` is LC-owned standard-cell logic. Its two 32 B gate/up input slots and two 16 B output slots total **96 B payload registers**, with output ownership retained through the actual S write ACK. There are two ordered response tags. It accepts 1–32 whole 128-bit words, four S32 values per word, in three disjoint contiguous S windows; other layouts and partial words are rejected or unsupported explicitly. It adds no SRAM and does not enlarge the existing private 16 KiB.

The three-phase ordinary-S128 calendar issues one gate read, one up read and one Mid write per four values. G computation overlaps these ordinary transactions inside the finite stream. It cannot overlap a native S_P feeder job. The measured continuous service to final write ACK is **3W+11 cycles**, for W four-value words: W=1/7/32 gives 14/32/107. Thus a 128-value frame performs 64 reads and 32 writes in 107 cycles, with 64 G input and output packets. This is neither the 68-cycle pure kernel nor a sum that charges compute and memory twice. Completion is asserted on the final ACK edge; the earliest synchronous LC take is the next edge and is separately recorded.

[Job 102104](g-sim-07/results/summary.json) passes five modes × three initial-state/seed pairs: normal, real S request/response backpressure, reset/replay, early overflow drain, and late overflow under backpressure. The joint test uses unchanged main S_P RTL and the actual hash-checked OpenRAM bank model, then reads back real SRAM Mid words. It uses the first 128 actual values from layer0/batch0 of the historical vector set. Continuous/reset traces are 107 cycles; the declared backpressure trace is 201. A late fault commits and acknowledges exactly three good words, never writes the failing word, drains all accepted work and reports `done_words=3`. LC must discard/replay a failed destination window; earlier SRAM commits are not rolled back.

[Job 102114 mapping](g-frontend-01/evidence/frontend/receipt.json) prices the adapter rather than calling the holds free: **7,506.254 µm²**, 874 DFF_X1 (768 payload bits plus 106 metadata/control state bits), 1,179 MUX2_X1, zero memory/hard-macro instances. This is mapped standard-cell area, not a routed area or 300 MHz result. It belongs in the P LC/adapter cost and physical implementation, outside the accepted G hard macro. Descriptor registration, actual LC integration, combined standard-cell placement/timing and full-system verification remain parent-task work.

## Reproduction and artifact boundary

Run `python project/experiments/w8a16_physical/results.py` from the repository root to rejoin local exact-byte receipts, six-file SHA bindings, final ODB identity, density floors, model coverage and S128 traces. [g32-results.json](g32-results.json) is the generated machine-readable result. Large native data remain in the authorized project store at the exact paths and SHA-256 values in [delivery.json](g-deliver-01/evidence/delivery/delivery.json); the repository keeps bounded original reports and [the native layout preview](g-deliver-01/layout.png).

Failures remain preserved: job102081 default persistent ABC transport stalled after output generation and was diagnosed/cancelled without changing the library; 102087 rejected an incomplete batch wrapper; 102112 rejected the historical issue143-only I/O-lock namespace before any geometry work. Later source-bound runs fix only the execution transport/profile. Original Liberty, original full FreePDK45 rules and original native electrical/timing boundaries are unchanged. The explicit G-only/10-or-12-CPU access specializations have a machine-checked exact diff in `profile-sources.json`; no geometric rule or source check is removed.
