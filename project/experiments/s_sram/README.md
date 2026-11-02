Final whole-S engineering result (2026-11-02): [report, exact source/artifact bindings and replay](../../../docs/S_SRAM_FINAL.md). Physical033/95227, independent final95229, strict formal95230 and join95233 all passed the unchanged300MHz gates, including full original GDS DRC=0. The accepted standard-cell S remains unchanged. Independent review/merge pending; TT schematic bank characterization only, internal bank wire PEX unimplemented and upstream HL-to-LH copying limitation retained. The following interface contract remains applicable.

# S SRAM variant (independent physical implementation)

Refs [Issue155](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/155),
with the unchanged S interface from [Issue143](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/143).
Original local test base: `9a248b38`, current branch `task/155-s-sram`. This optional variant is newly
authorized in the side conversation; it does not replace the seven-block
baseline, its standard-cell S, its source selectors, or its qualification.

## Resources and interface

- `block_feed_s_macro_sram` has the same functional ports as current
  `block_feed_s_macro`, with the unchanged `block_feed_loader` inside.
- `block_feed_s16k_sram` replaces only the payload store: four **256x128 1RW**
  SRAM instances, exactly16KiB, all using `s_sram_256x128_freepdk45`.
- Narrow word address: bank=`addr[1:0]`, bank row=`addr[9:2]`.
  Wide row concatenation is `{bank3,bank2,bank1,bank0}` (512 bits).
- Wide priority applies only when the wide request is actually accepted.
  A stalled wide response does not monopolize narrow-channel credits.
- A narrow write returns its accepted128-bit data, matching the current
  seven-block S contract (the older five-block S returned zero on writes).
- Both response channels have two entries INCLUDING any pending SRAM return.
  These buffers total160B plus128B feeder A queue and64B feeder B slot,
  metadata and command registers. The small control/holding registers remain
  standard cells; no hidden extra16KiB payload copy is introduced.

## Timing and reset

A request accepted at rising edge K is captured by SRAM. The reference OpenRAM
1RW interface performs the array operation on the following falling edge.
The wrapper captures the result at rising edge K+1. `valid` is asserted after
K+1; the earliest downstream acceptance is K+2. Relative to the current
standard-cell S, this adds one registered response stage. With the consumer
always ready, narrow or wide requests can still issue every clock after fill.
The unchanged feeder waits for `mem_valid`; its actual latency can increase.

Responses remain stable until consumed; retirement and refill may share an
edge. Only one narrow OR one wide bank operation issues per clock. All banks
are1RW; wide reads occupy all four, narrow requests enable only their bank.
No same-edge read/write collision or read-during-write value is assumed.

Reset synchronously abandons pending/queued responses and feeder commands;
all externally visible handshake enables are suppressed while reset is high.
Reset never clears SRAM contents. An accepted write can already have completed
before reset; reset does not roll it back. Initialize data before reading it.
Always provide the full rising/falling clock cycle; no ad-hoc clock gating.

## Verification

From a Linux environment with Verilator and C++ compiler:

```sh
python3 project/experiments/s_sram/run.py --out .local/s-sram-unique-run
```

The runner uses an explicit `S_SRAM_SIM` define for the **simulation-only**
two-edge macro stand-in. It runs strict lint and three actual initializations
for storage and the full feeder integration. Checks cover all1024 words,
128/512-bit sustained request rate, bank ordering, simultaneous contenders,
independent response backpressure, bounded in-flight capacity, write ack,
reset with pending work, retained payload, invalid descriptors and all
rows1..8/tiles1..4/S8-S16/reuse combinations. Read latency is tested explicitly.
Initialization modes are all-ones, random143 and random144. Numeric memory
traffic is deterministic to make regressions reproducible.

## Real macro integration

`openram_config.py` requests one256x128 1RW bank in **FreePDK45**, TT/1.1V/25C,
with DRC/LVS enabled. Four instances make the S payload. Run an actual OpenRAM
compiler in a separate output directory; record its version and all emitted
files. No fake LEF or empty GDS is supplied by this variant.

```sh
python3 project/experiments/s_sram/generate_bank.py \
  --compiler /path/to/OpenRAM/sram_compiler.py --out .local/new-real-bank \
  --internal-pins --words-per-row 2 --delay-chain-stages 25 --spice-threads 8
```

The current production candidate is **WPR2/control25**. Its minimum and maximum
load/slew preflight points passed every native delay check at300MHz; the full
physical bank and library are being regenerated in `generate-009`. This is not
yet a complete S GDS or final timing acceptance. The historical default
WPR4/control9 is not the selected implementation and failed transistor write
checks; always pass the explicit candidate arguments above. Characterization
uses actual Cartesian loads0.2091/1.6728/6.6912fF and slews5/40/160ps. Retain
the verified runtime/tool overlay receipts from the remote launch record;
changing library limits without simulating these points is not permitted.

This checked entry point requires Linux/KLayout/ngspice, preserves a missing
prerequisite receipt, disables implicit conda installation (not verification),
and requires all five emitted views plus nonempty FreePDK45 FEOL in the GDS.
It never labels generation alone as physical acceptance.

The physical source list must use the actual generated SRAM module declaration
and its matching Liberty, LEF, GDS and SPICE/CDL. **Exclude
`s_sram_256x128_freepdk45.sim.sv`** and do not define `S_SRAM_SIM` in physical
builds. Define `USE_POWER_PINS` only with the matching macro power ports;
the wrapper forwards explicit `vdd/gnd`. Map them to the block power grid.

Before physical acceptance, verify macro dimensions, pin/bus direction,
LEF obstruction/layer map, supply voltage/corner, actual clock edges and
minimum high/low pulse widths. Analyze both input setup/hold and SRAM
clock-to-output plus wrapper capture. A300MHz target is not proven by RTL
simulation. Re-run full block placement/PG/CTS/route/RCX/STA, native and full
GDS DRC, SRAM LVS and final function/strict equivalence with an appropriate
memory abstraction and its independently checked implementation. An unresolved
black box cannot count as whole-block equivalence. No physical/PPA qualification
from the standard-cell S transfers to this variant.

References: [OpenRAM compiler](https://github.com/VLSIDA/OpenRAM),
[actual model generator](https://github.com/VLSIDA/OpenRAM/blob/stable/compiler/base/verilog.py).

## Delivery scope

The variant runs independently under
`/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155`.
The Issue143 production queue and standard-cell S stay unchanged. Remote
inventory94535 confirmed KLayout0.30.12, but no ngspice/OpenRAM or SRAM GDS in
the Nangate45 platform. Built-in fakeram45 LEF/Liberty cannot substitute for
real SRAM geometry. Compute nodes cannot resolve external package hosts, so
the dedicated provisioning entry point verifies an offline SHA256SUMS before
installing Linux Python3.10 dependencies and building official ngspice45 source
under `/public/home/yuzelu/opt/eda/issue155-sram`.

The configuration explicitly requires ngspice transistor characterization
(`analytical_delay=False`), KLayout DRC/LVS and retained temporary evidence.
Actual generated views, macro DRC/LVS, complete S placement/PG/CTS/route/RCX,
300MHz timing, full merged GDS and functional/equivalence results are separate
acceptance gates. Neither successful provisioning nor a compiled bank alone
constitutes completion. See the current [remote evidence index](../../../work/YUZE-LU/155/README.md).
Original local interface evidence remains in `work/YUZE-LU/143/s-sram-variant`.


For the already routed, independently LVS-checked bank, `views_from_routed.py`
retains actual layout GDS/LEF and verifies the reconstruction before real ngspice
characterization. `simulator_overlay.py` fixes only the explicit non-Conda tool
launcher in an isolated package copy. No simulator results or physical checks
are replaced. The effective corner is explicitly TT/1.1V/25C. Original native
DRC and the complete ORFS bank/block DRC remain separate mandatory gates.
The KLayout PEX entry point in this OpenRAM version is not implemented: the
resulting library is schematic characterization, not SRAM internal post-layout
wire-RC timing. Complete S external SPEF does not remove this limitation.


SPICE diagnosis must retain the native sense-enable constraint as well as data
checks. The early ten-check 300MHz result omitted native acceptance: its retained
log has a failed `delay_sen0` measurement. It is not a qualified operating point.
`diagnose_array.py` evaluates alternative internal row organizations/control
lengths with all native checks and an independent half-period sense-enable
gate. It is explicitly netlist-only, produces no physical view or library, and
cannot bypass checked real generation, macro DRC/LVS or complete S routing.
