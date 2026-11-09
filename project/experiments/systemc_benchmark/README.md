# Qwen3B timing and energy benchmark

Issue [#234](https://github.com/rayggxia-workspace/LLMHardwareDesign/issues/234).
This is an incomplete calibration campaign. No complete device decode token/s
or J/token has passed acceptance. CPU oracle wall time is not device time.

## Reproduce each evidence level

Lightweight checks, from repository root:

```bash
python -B scripts/check_project.py
python -B -m unittest discover -s project/experiments/systemc_benchmark -p 'test_*.py'
```

Compile `timed_resources.cpp` with SystemC 3.0.1, C++17,
`-DSC_INCLUDE_DYNAMIC_PROCESSES`, its include/lib64 paths, `-lsystemc -pthread`,
and the matching runtime library path. `probe.py EXECUTABLE NEW_OUTPUT` checks
dependencies, concurrency, S contention, write ACK, fork/join and unknown energy.
This is synthetic engine validation only.

`baseline_trace.py IR PLAN FROZEN_TRANSITION NEW_OUTPUT` re-evaluates frozen
old220 costs from bindings and cache state, checking planned times and totals.
Planned times are never sent to SystemC. TSV predecessor edges express the old
append-only resource policy. `run_baselines.py` drives six old configurations.
Results validate the coarse old kernel cost model, not calibrated chip time.

Remote attempts use fresh directories under
`/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark/`.
Snapshot sources before submitting the matching `.sbatch` file. Heavy remote
work runs under Slurm on one node, six tasks times ten cores; tools and BLAS
are restricted accordingly. Queue/partition/time overrides and actual jobs are
recorded. Never overwrite a running attempt or change another task's allocation.

- `reference_decode.py CHECKPOINT NEW_OUTPUT --prompt-tokens 512
  --decode-steps 128 --threads 10`: complete FP32 numerical oracle, cached versus
  independent full-prefix checks. Three contexts and two prompts have run.
  It emits 128 tokens (first from prefill), and executes 128 cached calls;
  the final call is extra numerical warm-through. Standard generation of 128
  tokens needs 127 cached calls after TTFT. Exclude the extra call when timing
  that scenario; never divide all calls by a different token count.
- `export_cached.py CHECKPOINT NEW_OUTPUT --prefix 128 --query 1 --threads 10`:
  complete 36-layer explicit KV graph with last-query logits. All 72 KV outputs
  and logits must match HF and ORT. Export and integer mapping are separate.
- `capture_operands.py FROZEN_SOURCE OLD_IR NEW_OUTPUT`: stop immediately before
  first Q projection and capture actual integer operands from three old inputs.
  Optional bounded weight pack qualifies only this prefix, never a full model.
  The original C++ primitive oracle remains the numeric reference.
- `m_activity.py`: run captured operands on RTL and routed M netlist; check S64
  products and native Execute cycles; collect VCD and extracted-RC power. Needs
  accepted M RTL, `operands/`, full views, original Nangate power library,
  OpenROAD/Yosys/Verilator. Local path/worker flags are in `--help`. These M
  samples alone never qualify full energy.
- `power_inventory.py`: load full routed M/E/G/N/S-base/S-P and original SRAM
  power library. No VCD is loaded: default power is explicitly unqualified.
  Timing-only abstract Liberty cannot substitute for full physical views.

`energy.py` accounts continuous idle (including local clocks/leakage) plus
incremental activity. Subtract idle over the measured active window before
integrating increments. Parent clocks, controls, wiring and DDR outside leaf
calibration require explicit separate coverage. Missing entries leave total null.

## Qualification and comparison

`acceptance.py` is a metadata screening gate, not an independent validator of
the provenance behind its fields. Final acceptance needs artifact audit,
coefficient coverage, uncertainty, numeric quality, common checkpoint and actual
native best-configuration search receipts. Preserve FPGA's native packing,
quantization, memory layout and scheduling; report quality and resource budgets.
Do not claim a global optimum without proof. Match timing/energy boundaries or
report separate non-comparable results without a pass claim.

Job ledger, peer freezes and remaining gaps: [work234](../../../work/YUZE-LU/234/README.md).


## Activity and native peer calibration

`analyze_activity.py PHYSICAL LIBERTY VCD FUNCTIONAL_RECEIPT NEW_OUTPUT`
requires matching functional interval, 1ps VCD, matching scope and nonzero
activity annotation. `classify_m_activity.py` joins remaining pins to actual
OpenDB identities and original diode power tables. Missing chip components
and delay-induced glitches remain missing, never filled with zero.

`m_streams.py` / `m_tiles.py` take a SHA-locked compiled M model, manifest,
Verilator include directory, operands, physical directory, original library
and fresh output. Only the driver is rebuilt; independent Python S32/S64
arithmetic precedes active/matched-state idle analysis. `--narrow-correction`
uses native S8 for the exact 0/1 component. This is software service evidence,
not DP performance. The window excludes decomposition, S feeder/LC/DMA,
final readout and destination acknowledgement. `m_profile.cpp` sweeps native
descriptor shapes and checks direct S64; replicated rows test timing only.

`prepare_opentpu_qwen2.py FROZEN_PEER NEW_OVERLAY` adds bias at every native
QKV projection site including tiled prefill. `opentpu_qwen2_smoke.py` checks
HF, original quantization emulation, resident decode and prefill; three tiny
seeds/two formats are separate from full-3B quality. HF differences are kept.
`opentpu_native_timing.py PEER CHECKPOINT HF_REFERENCE NEW_OUTPUT --format int8`
compiles all 36 layers using resolved native m4 features and four-GiB capacity.
`--compile-only` never runs a model. Otherwise zero-data RTL/LiteDRAM cycles
are single-step timing diagnostics, not a qualified best continuous decode
score. `compile_step`, resident decode and native generation use the same
`qwen3_step` kernel, but the resident loop, token selection and host overhead
are absent from this probe. Do not let the two-GiB convenience co-sim helper
exclude a legal int8 candidate. Build parallelism alone is capped to allocation.
Candidate frequency requires physical evidence; zero data cannot qualify
accuracy or workload energy. `opentpu_native.sbatch` runs six full-size cases.

`peer_toolchain.sbatch` probes pinned official LLVM23.1.1 in the EDA container
before native llaccel compilation. Tools present are not successful compilation
or PPA evidence. Detailed job/source receipts are in the work234 ledger.

`m_profile.py DIRECTORY CACHE_RECEIPT OUTPUT` validates all 8192 native descriptor rows and three agreeing initialization runs; exact lookup has no unmeasured extrapolation. Frozen drivers and input operands are archived. Measured load/Execute/readout still exclude S/LC/DMA.

The user-confirmed public benchmark contract and source snapshots are indexed in [BENCHMARK_CONTRACT](../../../work/YUZE-LU/234/BENCHMARK_CONTRACT.md). No FPGA board reproduction is required. Public cross-model figures are context, not falsified common-checkpoint acceptance evidence. Speed and J/token must both pass; ~10 token/s is not a substitute for the actual peer result.


## Runtime-state frontend probes (not full generation coverage)

`cached_primitives.py` preserves the pinned old220 integer recipes and adds
explicit runtime S16/S32 state inputs, token/state shape checks and exact Neg
lowering. KV is never labeled a checkpoint weight. Host last-use release and
`exact_reference_dot.py` only accelerate numerical validation; they do not
change generated service costs, memory traffic, or silicon performance.
The accelerated oracle proves all binary64 integer partial sums exact and
all S64 reconstruction bounds, otherwise falls back to signed integer matmul.

`cached_integer_probe.py FROZEN EXPORT WEIGHTS CHECKPOINT ORACLE NEW_OUTPUT`
checks three full-size one-step samples and every KV output against HF.
Input KV originates in HF, explicitly quantized; it does not qualify an
integer-generated sequence. Optional `--compare-baseline` checks all output
bits against the frozen adapter before host optimizations. `cached_integer.sbatch`
is six tasks by ten cores. The first submitted campaign is an older frozen
snapshot; source/attempt/results must be matched before drawing conclusions.

`e_activity.cpp` / `e_activity.py` / `e_activity.sbatch` pair scalar compact-E
Min/Select activity with matched-state idle. RTL/netlist and three initialization
runs must agree before extracted-RC activity analysis. The captured-derived
operand patterns are representative samples, not an entire compiled E trace.
Unclassified pins/glitches and all other chip/DDR components remain missing.
`memory_budget.py` gives conditional weight-traffic floors with declared cache
capacity; none of its hypothetical packed formats qualifies accuracy or hardware.

`cached_template.py NEW_OUTPUT --tiny --check-specializations` validates a
dynamic-past FP32 template and three fixed-position specializations. With
`--checkpoint PATH`, it checks the complete model at 128/512/2048 prefixes.
Parameters remain external; a position's mask/rotary constants are folded only
when specializing that position. This saves host tracing, not device time.
`kv_handoff.py` accepts every layer's signed S32 output directly as the next
program's runtime input, rejecting missing states, length/scale/range changes
and accidental weight contracts. Format conversion requires an explicit device
service. Unit tests are not evidence of a continuous 3B integer sequence.

`frontend_full.sbatch` runs six full-size fixed prefill/decode shapes, the
latest exact host replay, and reusable-template checks, in six exclusive
ten-core steps on one node. Export and integer failures remain separate; a
failed FP32 threshold cannot be erased by a passing integer check. Source and
attempt receipts must be matched; this campaign is not complete generation,
SystemC system timing, or chip energy.

`tiny_chain_probe.py SPECIALIZED FROZEN NEW_OUTPUT --oracle-command '["ORACLE"]'
checks a two-layer three-step integer state chain. `--include-prefill` starts
from a separately traced empty-cache two-token prefill. All later KV is taken
from emitted integer outputs through `kv_handoff`, never replaced with HF.
Optional `compile_program(output_formats=...)` adds actual `Convert` primitives
to maintain stable state exponents; their cost must be included downstream.
This fixture passed all logits/KV checks but does not qualify a 3B sequence.

`s_activity.cpp` / `s_activity.py` / `s_activity.sbatch` characterize ordinary
128-bit transactions on both accepted compact S variants. The original bank
Verilog labels its DELAY/T_HOLD arbitrary; `s_functional_bank.py` makes a
SHA-locked task-owned zero-delay activity view. It does not change the accepted
source or original TT Liberty, and does not qualify fmax or glitches. The power
runner loads original bank Liberty with `analyze_activity.py --extra-lib`.
Serialized read/write/ACK, stalled responses and memory contents are checked
independently. Feeder traffic and whole-chip energy remain separate.

`analyze_activity.py` rejects less than 99% pin annotation and records actual
coverage before failing. Remaining pins still need a physical/library audit.
`--escape-sta-backslashes` escapes literal backslashes in VCD scope/reference
names for STA lookup, preserving identifier codes, values and event order.
The E/S gate builds use depth two to include standard-cell pins. The original
shallow E power coefficients are rejected, despite functional/tool completion.

`n_fixture.py OPERANDS '["ORACLE"]' NEW_OUTPUT` derives three captured S16
cohorts, cross-checks factors with independent Python integer square roots,
and obtains factor/relative-exp answers from the frozen native reference.
`n_activity.cpp` checks serialized commands, stalled responses, RTL/gate and
three initializations before active/matched-idle power analysis. RMS uses
24-element vectors; L2 and relative-exp samples are scalar. These samples
do not qualify every N instruction distribution or whole-chip energy.

The frozen old220 `n_soft_stats` template uses count one, whereas the native
reference relative-exp semantics require `Stats(count=2, [x,0])`. Count one
computes a different maximum on negative x. The accepted gate model reproduces
this failure; both commands happen to take four cycles in these samples.
No parent source is changed, and frozen symbolic native templates must not be
called numerically qualified end-to-end. See the work234 native-gap receipt.

The one-step integer probe also reports error of dequantized S16-weight FP32
versus original HF, and integer versus that FP32 graph. These are attribution
diagnostics; the original HF quality criterion is unchanged. Failed checks
remain failures even when logits argmax agrees.

`contraction_bounds.py` refines the old max-times-length accumulator bound with
integer row/column L1 bounds only when needed. The unsigned norm reduction is
itself proved safe before use. The component norm covers every signed-low16,
signed-high16 and correction partial product; the S64 gate is not removed.
Independent arbitrary-precision checks cover sparse long contractions and
unsigned-reduction overflow. This changes a proof, never the emitted arithmetic
or device timing. Full-size failures remain pending re-evaluation.

`sequence_replay.py FROZEN NEW_OUTPUT --checkpoint CHECKPOINT --weights MANIFEST
--tokens REFERENCE_TOKENS --oracle-command '["ORACLE"]'` starts with integer
prefill, then selects every next input from its own integer logits. HF supplies
separate calibration inputs and independent comparisons, never live KV.
`--steps-this-run N` and `--resume PREVIOUS_OUTPUT` implement bounded batches;
resume verifies state, calibration, template, sources, checkpoint and raw S16
parameter identities. Reuse `--decode-template` and `--prefill-onnx` to avoid
re-exporting unchanged graphs. Stable S32 KV scales require visible Convert
instructions. A failed quality check is preserved and stops the batch.

`sequence_replay.sbatch` reserves one node with six ten-core workers for
P128/P512/P2048 and two frozen natural prompts. The first campaign requests
only one generated token, not the entire D128 scope. The two largest host
calibration jobs share a lock to limit simultaneous retained ONNX tensors;
this has no effect on device scheduling or measured token/s. The tiny fixture
passed first-two/resume-two versus uninterrupted-four bit-exact KV comparison,
but neither this nor job submission qualifies full 3B generation or SystemC.


## SystemC/DRAMsim3 transport audit and program inventory

`systemc_dram.cpp` is a clocked SystemC queue/dependency bridge to DRAMsim3,
not an extension of the old DP makespan. `dram_probe.py` checks six synthetic
cases against a separate direct DRAMsim3 replay of accepted transactions,
including complete callback and counter equality. Build the pinned upstream
DRAMsim3 `29817593b3389f1337235d63cac515024ab8fd6e` and use SystemC 3.0.1:

```bash
g++ -std=c++17 -O2 -Wall -Wextra -Werror -I"$systemc/include" \
  -isystem "$dram/src" -isystem "$dram/ext/headers" systemc_dram.cpp \
  -L"$systemc/lib64" -L"$dram" -Wl,-rpath,"$systemc/lib64:$dram" \
  -lsystemc -ldramsim3 -pthread -o systemc-dram
python3 -B dram_probe.py ./systemc-dram "$dram" NEW_OUTPUT
```

The upstream includes are system headers; warnings in our code remain errors.
The bridge requires explicit 64-byte bursts and a 1-ps-representable clock.
Write callbacks mean buffer acceptance. The stock separate-queue read-to-write
fixture returns every callback while leaving four write commands unissued;
its incomplete window is a preserved negative example. A separately labeled
`unified_queue=true` candidate drains that fixture; it is no claim of an
implemented hardware memory controller. Configuration differences are retained.

In this pinned upstream version, `total_energy` is V*mA*cycles despite its pJ
label. The driver independently reconstructs IDD command/background accounting
and multiplies by `tCK_ns*1e-12` for joules. A twofold clock-period fixture
checks these units; that fixture is never a physical candidate. Generic DRAM
parameters do not qualify a selected part. PHY/controller/termination/VPP and
board overhead are excluded, so these runs cannot produce total J/token.

`program_inventory.py PROGRAM NEW_JSON` independently counts full-shape Dot
work and the existing append-only primitive allocation subtotal. It also gives
an abstract full-buffer liveness estimate in emitted sequential primitive order:
views retain their entire backing allocation, results are allocated before
last-use sources are freed, and returned KV remains retained. This is **not an
implemented allocator or a valid parallel-DP lifetime schedule**. Immutable
weights, predicates and component scratch are additional. Neither storage
figure is CPU peak memory. Three alias/runtime-input fixtures check this model.

The full 36-layer programs agree with an independent Qwen MAC formula. For
P0Q512, append-only primitive addresses total 409.325 GiB, whereas the proposed
serial lifetime model peaks at 864 MiB plus excluded storage. This exposes a
backend allocation problem, not a required model capacity or DP search gain.
Changing allocation or native arithmetic recipes requires its own validation
and must be separated from an algorithm-only speedup.

`cached_integer_probe.py --trace-first-layers N` optionally records canonical
outputs of the first N layers against a dequantized-S16-weight FP32 graph,
before last-use release. The observer changes no arithmetic and the original
HF quality checks remain intact. The six small full-3B shapes are localization
experiments, not full-generation timing evidence.


## Clocked S feeder calibration and RMS diagnostics

`systemc_feeder.cpp` models the real finite A/B queues, one outstanding SRAM
request and held completion. Build with SystemC3.0.1, C++17, `-Wall -Wextra
-Werror`, then run `feeder_timing_probe.py EXE RTL_GATE_BINARIES OPERANDS
NEW_OUTPUT`. The probe samples pre-edge handshakes and compares every packet,
completion and ACK against32 actual jobs in each of six RTL/gate configurations.
It does not replace M/LC/MC or calibrate whole-system time.

`s_feeder_activity.cpp` checks data against an independent complete SRAM array.
`s_feeder_activity.py` uses accepted physical views and the original bank lib,
including full pin activity and explicit idle power. Exactly seven disconnected
trace bits are excluded from cross-initialization trace comparison after proving
that no netlist cell references them; original VCD power input remains unchanged.
The negative proof fixtures reject connected bits. Activity includes amortized
quiesce commands, so these coefficients are not claimed as pure transfer energy.
Host SIGSEGV failures and bounded same-input retries are preserved separately.

`cached_integer_probe.py --capture-kernel CANONICAL_RMS_ID` optionally captures
real integer input, all emitted intermediates, gamma/epsilon and DQ-FP32 input/
output, with source/program/array SHAs. The old quality gates remain unchanged.
`rms_capture_replay.py FROZEN CAPTURE_NPZ PROGRAM NEW_OUTPUT --oracle-command
'["ORACLE"]' requires baseline output bit equality before testing extra iterations.
`rms_refinement_probe.py` retains extreme heterogeneous-row failures, including
an eight-iteration case still37.5% away from FP64. The default one-refinement
compiler remains instruction-identical to frozen220; explicit extra iterations
are an accuracy-repair candidate and never counted as DP gains.
`nonlinear_probe.py` supplies independent FP64 comparisons on conventional
quantized distributions; those successes cannot qualify the full checkpoint.


## Mother activity and diagnostic continuation

`mother_activity.py ACCEPTED NEW_SOURCE` instruments only the accepted public-port
fixture: observation ports, rational300MHz clock, and deployed-program idle branch.
Build RTL/gate with `mother_activity.cpp`, Verilator5.042 `--trace-underscore
--trace-depth99 --timing --trace`, then run `mother_probe.py ACCEPTED BINARIES
ORIGINAL_STD_LIB NEW_OUTPUT --power`. All existing assertions remain enabled.
The three finite-peer fixtures qualify neither Qwen service latency nor nine
resident targets. Idle PM/clock energy remains separate from activity increments.

`analyze_activity.py --audit-unannotated-diodes` reports raw coverage unchanged.
It permits exclusion from the functional-pin denominator only after **every**
remaining pin is matched to this ODB and the original ANTENNA_X1/A zero-own-power
Liberty tables. Input capacitance remains in the circuit. Any ordinary cell or
incomplete identity/count proof fails. No generic waiver or lowered threshold is used.

`sequence_replay.py --diagnostic-continue-after-quality-failure` preserves all
failed checks while collecting further integer-generated tokens. Resume hashes
include the policy/source identity; failed ancestry can never qualify a sequence.
It still rejects changed sources/states, overflow and invalid KV. Diagnostic
process completion is not numerical, timing or energy acceptance.

Real capture replay demonstrated that additional RMS iterations fix an isolated
seed error but leave upstream low-amplitude-token error. The observer now reports
last-axis rows as well as a tensor norm so outlier rows cannot hide that error.
The original default recipe remains in use.

## Clocked mother runtime and finite backing allocation

`systemc_mother.cpp` independently executes deployed compact CALL/WAIT/MOVI/END
images, PM bank/pending responses, finite credits and return arbitration. Build
with SystemC3.0.1 and C++17, `-O2 -Wall -Wextra -Werror`, then run
`mother_timing_probe.py EXE ACTIVITY_OUTPUT ACCEPTED_TREE NEW_OUTPUT
--binaries RTL_GATE_BINARIES`.
All eight CALL argument words, retirement, return, done and ACK are compared
against pre-edge actual RTL/gate VCD. The five fixtures cover MOVI and concurrent
returns as well as held calls. They cover two resident targets, not deployment,
EVENT/fault behavior, nine-target integration or Qwen timing/energy.

`bounded_memory.py PROGRAM NEW_PLAN --capacity-bytes N --scratch-records N`
implements finite best-fit addresses and last-consumer reuse in **serial**
primitive order. Views retain whole backing allocations; immutable complete
dense permutations share their proven file storage with explicit strides.
Constants and predicates are actually reserved/preloaded; scratch is explicit.
An independent address/time interval audit rejects live overlap. Tests cover
OOM, stale generations, alias lifetime, transposed values and late constants.

`bounded_addresses.py FROZEN PROGRAM PLAN OBSERVED_ONNX NEW_AUDIT` additionally
checks original frozen view/Dot/broadcast/Gather index programs, including
allocation lifetime and physical-file strides. The six full-shape address
audits sample boundaries/midpoints of every primitive; they are not exhaustive
numerical RAM replay or parallel-DP qualification. ONNX1.17.0 is a private graph
parser dependency; its installation is not a device performance result.

The 64GiB diagnostic plans include unpacked128-bit scalar records and explicit
native scratch; they exclude full control/program-image storage. They do not
select a physical external-memory capacity or increase the frozen memory budget.
Actual peak/high-water values and sources are recorded in the Issue234 ledger.
No timing/energy speedup is attributed to this allocator before integration.

`cached_integer_probe.py --rms-refinements 1..8` explicitly labels a nondefault
numerical-recipe candidate in both program and receipt. The default remains1.
This option has not established a full-model quality fix or DP-only gain.

`--weighted-product-fraction-bits 0..6` is another explicit numerical candidate,
default0. It retains finer S32 output only for a canonical Mul directly feeding
a Dot with an immutable S16 RHS. Calibration reserves S32 range; existing exact
S64 accumulator/component checks remain mandatory. Runtime S32xS32 contractions
are excluded. Neither operation count nor physical storage width is changed by
this policy, but lowering cost must still follow the changed operand values.
The recipe and each exponent change are recorded. A two-row outlier test checks
the projected result against exact independent integers; it does not establish
full-model accuracy or device speed. The frozen baseline remains separate.

## Native M timing and integrated P_64 activity

`systemc_m_execute.cpp` independently models the two partial banks, product/
reduction stages, serialized two-lane scale fetches and atomic commits. Build
with SystemC3.0.1/C++17, `-O2 -Wall -Wextra -Werror`, then run
`m_execute_timing_probe.py EXE NATIVE_GRID_DIRECTORY NEW_OUTPUT
--native-receipt NATIVE_RECEIPT`. The directory contains the three native grid
files and other evidence named by the receipt; a referenced compiled-model
manifest may reside in its parent directory.
The 8192 valid resident descriptors match all three native initializations;
five unsupported descriptors are rejected. Native evidence and every input
hash are checked. Load arbitration, stalled replies, LC/S/DMA, payload math
and full-model timing/energy are outside this Execute model.

`p_control_activity.py ACCEPTED ACCEPTED_RECEIPT NEW_SOURCE --bank-source
ORIGINAL_BANK` instruments the existing P_64 public-port fixture. All original
data/ACK/assertions remain enabled. Its explicitly zero-delay SRAM activity
view removes arbitrary behavioral delay decoration, not characterized timing
constraints. Build RTL and final-parent-netlist binaries with
`p_control_activity.cpp`, Verilator5.042 and `--trace-underscore --trace-depth99`.
Then run `p_control_probe.py ACCEPTED ACCEPTED_RECEIPT BINARIES ORIGINAL_STD_LIB
NEW_OUTPUT --power` with OpenROAD available on PATH.

One deployed native program takes363 cycles in RTL and the accepted parent
netlist across three initializations. Matched idle is measured separately.
Parent M/G/S Liberty views are timing abstracts; their internal energy is
excluded. The sampled parent increment varies0.451..0.782nJ by initialization,
and must remain a range rather than a generic LC service coefficient. All
six parent power analyses retain original Liberty/RC and audit1427 remaining
diode inputs individually. This does not qualify Qwen timing or total energy.

`systemc_n_service.cpp` models paired statistics plus the shared64-step divider
and32-step square root, including group handshakes and parent observation.
`n_command_profile.cpp` reuses the public-port driver/assertions in
`n_activity.cpp`; it can link the previously qualified RTL/gate object libraries.
Run `n_service_timing_probe.py SOURCE RUNS CACHED_NATIVE_OBJECTS FROZEN NEW_OUTPUT`
with the matching SystemC library on LD_LIBRARY_PATH. It audits all fixture
hashes, independent factor answers, six native logs and the SystemC log, and
executes eight invalid-descriptor rejection checks.246 services cover RMS/L2
lengths1..2048 with packet counts1..8, Exp and the legacy Exp counterexample.
All1476 native executions match; this is resident timing, not S/LC integration.

The old native Exp template is semantically wrong for negative inputs: one
Stats value makes its maximum equal to itself and returns exp(0). The corrected
leaf recipe is Begin softmax, Stats(count2,[x,0]), Finalize, Exp(count1,x).
The experiment proves seven negative-input mismatches. No parent compiler source
is changed. Packet construction has a separate public-service qualification below;
deployed LC lowering remains outside both experiments.

`recipe_matrix.sbatch NEW_OWN_ROOT` is an explicit numerical experiment:
P128/P512 prefill and P512 decode, each with RMS1/2, all with six finer weighted-
product fractional bits. It freezes the same checkpoint/weights/quality gate,
uses six10-core workers on one node and bounds this experiment to30 minutes.
It changes emitted numerical recipes, never the fixed macro count or claimed
DP-only gain. A timeout or failed quality gate remains an incomplete result.

`n_exp_packet_fixture.py REPOSITORY NATIVE_FIXTURES NEW_OUTPUT` reuses the U-group
public-port fixture and its original private-S/ACK assertions. Existing E13
narrows canonical S32 to a complete128-bit `[x,0]` packet, stores/reads it in S,
then executes N Begin/Stats2/Finalize/Exp1 and stores/reads the answer. Eleven
native reference values, including negative extrema, pass three initializations
and three-cycle held-completion checks. This is an existing-hardware service
recipe, not a generated LC program or new DP performance gain. An integer1ps
clock verifies3333/3334ps positive-edge spacing at rational300MHz; fractional
real-time conversion failures are retained. Bank activity behavior is explicitly
zero-delay, so this functional timing experiment is not physical STA acceptance.

`systemc_u_packet.cpp` independently advances the shared private-S arbiter,
registered bank response, E/N service read/execute/write/ACK states and resident
pipelines. It reads no measured service latency or precomputed starts. Build
with SystemC3.0.1/C++17 and `-O2 -Wall -Wextra -Werror`; run the resulting binary
without arguments. Generate RTL with `n_exp_packet_fixture.py --timing-trace`,
then run `u_packet_timing_probe.py SOURCE RTL_RUN SYSTEMC_RUN NEW_OUTPUT
--bank-source QUALIFIED_ACTIVITY_BANK --systemc-library MATCHING_RUNTIME`.
The audit checks source/runtime/reference hashes and every command, S request/
response and completion/ACK event against three actual RTL initializations.
341 events per initialization match exactly. This packet recipe remains serial:
two-client simultaneous S contention, LC/PM/deployment, full Qwen and energy
are unqualified. The fixture's artificial holds/readbacks are modeled explicitly
and its total time must never be used as a generic per-Exp service coefficient.
