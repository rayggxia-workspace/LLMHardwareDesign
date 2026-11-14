# Native S32 attention service and DDR staging

Refs #252 and draft #253. Native compute has a real four-bank S128
functional proof. No route, frequency, energy, or system throughput is
accepted by this report.

- `run-10` preserves a strict-build parser failure. `run-11` / 102444
  passes 108 trials across three lane capacities, six seeds, three initial
  states, two pressure modes, K128/K512 and both layouts. Six complete
  request/ACK/operand traces were independently audited. This includes
  using previously committed A and QK B from the actual four SRAM banks
  across successive result owners. Non-pressure service fees are identical
  to 102419. The pressure samples differ; do not reuse the older envelope
  silently. `native-s32-fees-102444.json` binds the new timings.
- `stage-01` preserves the original runner allow-list failure.
  `stage-02` / 102465 and `stage-03` / 102473 pass 36 trials each. The
  latter adds a real explicit fabric-rejection path (no fabricated data
  return/ACK). The existing MC aperture's 64 B stays held while one S128
  port writes two or four words. Without stalls, raw-first→last actual S
  ACK is 4 or 6 cycles, raw-first→raw take is 5 or 7 cycles, and the DONE
  event can be held independently. Existing SRAM is unchanged; no payload
  register duplicates the 64 B slot. Two local control descriptors, two
  accepted S write owners. The fixture is actual S with a held MC-interface
  peer, pending the joint three-P typed DMA test.
- `map-01` retains the original mapping and rejects the S128 envelope on
  unpruned portless Yosys scope metadata. `map-02` / 102446 flattens with
  `-noscopeinfo`, still requires all cells from the exact original Liberty,
  and binds the same RTL proved in 102444. Its area includes the full S128
  frontend and compute core; it excludes LC, stage64, S SRAM, or unrelated
  top-level glue. These are mapped cells, not post-layout occupied area.

| Query rows in hardware | Signed32 multipliers | Mapped logic (µm²) | Signal pins | Flops |
|---:|---:|---:|---:|---:|
| 1 | 4 | 118,333.558 | 822 | 8,998 |
| 2 | 8 | 206,440.206 | 824 | 14,032 |
| 4 | 16 | 374,252.690 | 828 | 24,100 |

The direct aperture pins are costly for the smaller shapes. The 16-lane
candidate is in an original M1–M10 route at 940×940 µm (102486). Actual
compact occupancy, ODB netlist regression/equivalence, real pin access,
electrical/PG checks, setup/hold and full original DRC remain separate.
All source/receipt artifacts are byte-pinned; large generated remote
reports and netlists stay under the immutable run path and are indexed by
SHA rather than silently substituted.
