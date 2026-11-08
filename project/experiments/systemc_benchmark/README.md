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
