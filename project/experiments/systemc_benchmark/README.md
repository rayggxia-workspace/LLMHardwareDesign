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
qualify dense timing only. Do not let the two-GiB convenience co-sim helper
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
