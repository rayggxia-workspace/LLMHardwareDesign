# Current bounded control verification matrix

Issue179 / Draft PR180; Melodydt. This campaign extends the existing host replay without changing qualified controller RTL, v2/64-bit ISA or the 3.333333333 ns implementation target. Functional benches retain the bank model's 10 ns clock. It qualifies nine fixed profiles, not arbitrary model graphs or topologies.

## Profiles and cases

`five/U,F,C,P,J` use two blocks of the same type. `recovery/U,F,C,J` use source0 to destination P1. Both PM implementations and initialization modes 1/143, 2/143, 2/144 are exercised. The existing native topology/ABI and upstream lock remain authoritative.

`cases.py` defines baseline, signed values, saturation/clamping, upper S-address boundary, legal lengths 1-4, consecutive jobs, three controller PM response-error targets, three lost-response targets, CRC corruption and maximal nonzero identities. Length crosses apply to directed links and J fragments/output; same-type U/F/C/P have no such link. Consecutive jobs use a saturating job followed by a healthy job, checking stale status is cleared. Maximum identity includes uint32 generation/job/START/image limits, J's 8-bit epoch and 24-bit tag limits; rollover is not supported.

PM faults are testbench injections on actual MC/LC0/LC1 response interfaces. Lost responses wait for actual poison/not-ready before external cohort reset and reload. `run_hold.sh` adds four observation clocks before that reset, so state8 and reset transitions are sampled rather than inferred from PASS. `run_identity.sh` independently runs the final identity boundary supplement. Existing five/recovery scenario assertions remain active, including commit, ACK, cancellation, quarantine/retry and held responses.

J clamping is checked numerically. Its current native done interface has no saturation flag: J RESULT saturation diagnostics are not qualified by this campaign. Failure results do not validate partial output. U/F/C length tests use fully initialized host carrier buffers; they do not pretend a one-word arithmetic producer generated four words.

## Coverage and evidence

`matrix_probe.sv` observes real lifecycle/sequencer states, lifecycle transitions, retired opcodes, host/native handshakes and recovery supervisor states. The collector checks exact scenario multiplicities, one PASS per log, raw coverage presence and every result-index SHA. It merges observed masks and Verilator LCOV DA records. Required bins are reported separately from line coverage; a missing required bin is a closure failure, not an exclusion to add after the fact.

Lifecycle states are required per target/controller; native sequencer states cover the recipe's subset. Generic compact-controller fixtures supply MC BIND and LC REPORT/opcodes outside native recipes. Opcode coverage is global across those fixtures and native paths; it is not every opcode on every block. Lifecycle transitions are the explicitly enumerated normal/reset subset, not all possible state pairs. Recovery supervisor states apply only to the four directed profiles. Line coverage is the union of selected non-test control source lines; it is not branch, toggle, per-instance or cross-product coverage. Unhit lines are retained in the evidence index.

Expected final scope: 248 unique target/case crosses; 1542 native RTL executions (1434 main +54 state-hold +54 identity), 148 generic RTL cases, 27 observer mutations rejected. Software is 1218 existing checks plus 141 matrix checks, counted once. Actual totals, observed bins, source/output hashes and limitations are in [validation](../../work/Melodydt/179/control-matrix-validation.json). Preliminary smoke runs and a corrected fixture status expectation are retained as history, not added to these totals.

## Reproduction

Run simulations on the authorized server using Slurm, within its resource rules. Paths below are placeholders, not production locations.

```bash
python3 -B project/control_task_compiler_v1/test_compiler.py --out /results/compiler.json
python3 -B project/control_matrix_v1/test_matrix.py --out /results/matrix.json
KIND=0 LAYOUT=1 NATIVE_STAGE=/inputs/stage SRAM_BANK=/inputs/bank.v VERILATOR=/tools/verilator BUILD_JOBS=4 bash project/control_matrix_v1/run.sh /results/variant-5
# Repeat KIND 0/1/2/3/4 LAYOUT=0 and KIND 0/1/2/4 LAYOUT=1.
# Same environment, independent output directories:
bash project/control_matrix_v1/run_hold.sh /results/hold-variant-5
bash project/control_matrix_v1/run_identity.sh /results/identity-variant-5
```

`run.sh` builds with `--coverage-line --coverage-user`, writes a separate coverage `.dat` for each execution, then invokes sibling `verilator_coverage --write-info`. `generate.py` emits task/input/mirror images and host replay; `instrument.py` derives observer/fault benches from existing fixtures, leaving control sources and prior assertions intact. `prepare_hold.py` and `prepare_identity.py` prepare only supplemental runners. `aggregate.py --root CAMPAIGN_ROOT --out collected.json` expects frozen r001-r005 layouts and core/software receipts, and independently verifies the files before merging observations. Collector Python must support existing project annotations; use the campaign's Python3.10 container, not an older login Python.

Tool evidence: Verilator5.042, Python3.10.12, Singularity4.3.4, orfs-26Q1.sif. Coverage behavior follows [simulation coverage](https://verilator.org/guide/latest/simulating.html) and [coverage utility](https://verilator.org/guide/latest/exe_verilator_coverage.html); latest documentation does not change the recorded execution version.

## Compiler correction and limits

The compiler now tracks `(buffer, word)` validity. Single-word U/F/C/P producers initialize only word0. JOIN/RECEIVE initialize their full produced ranges. SEND and P's four-word feeder reject any uninitialized word. Four targeted negative regressions supplement positive matrix cases. Declared `initial=true` still obliges the host to fill the entire buffer; it is not a numeric-domain proof.

No complete LLM/ONNX graph import, arbitrary scheduling, dynamic shapes, branch/loop generation, numeric format conversion, multi-clock CDC/RDC or physical acceptance is claimed. No new mapped STA, area, power or CTS run is part of this step. Next is stage9 synthesis delivery freeze, not a claim that synthesis or physical signoff is complete.
