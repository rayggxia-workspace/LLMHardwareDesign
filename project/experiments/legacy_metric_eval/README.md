# Issue247 old evaluation system replay

Use the unchanged SHA-locked `sram_port_compare.generate_policy` binary. Fixed:
S32 input services/S96 accumulator candidate, 300MHz, 2P/1U, 17.1GB/s aggregate,
32 credits, K256 queued/pipeline, four vector lanes, U16KiB, and all existing
cache/prefix/pair/write-combine recipes. This does not use `native_serial`,
native digit conversion, native command fees or run14's conditional adapter.

The21 actual runs are in `plan.json`: four workloads × four16KiB factors
(ctx1/shared, ctx8/shared, ctx1/ideal1R1W, ctx8/ideal1R1W), then four capacity
references (decode512W8 and prefill2W8,48/64KiB,ctx1/ideal1R1W,policy16), then
decode512W8 `observe`/ctx1/shared original baseline. All main factors and observe
use policy0; switch=1, reuseA=1, q4 means each modeled64B port occupies1cycle.
W8 uses `adaptive_prefix_pair_combine`; W16 uses `adaptive`. Negative W16
context results and the prefill context no-op stay in the table.

Current native four1RW banks do not justify `dual=1`: four16B bank operations
give64B total per edge, while the ideal model can read64B and write64B together.
The shared-calendar/ctx8 result is a conservative no-extra-port-credit study
reference, not a mathematical bound or measured native score. Ideal1R1W is
reported separately as a target. Consumer-priority arbitration has no separate
client-arbiter parameter in the old model; do not book an extra gain or rename
the existing adaptive prefetch policy as that native RTL feature. Native
eightS64 result slots also do not qualify the old eightS96 register contexts.
The48/64KiB references are not implemented capacity.

Server layout: `ROOT/source` is the locked repository, `ROOT/inputs` contains
the same frozen inputs, `ROOT/inputs.json` locks source/input files and a real
source commit. Also provide `ROOT/run01-result.json`, `run04-result.json`,
`run05-result.json`, `run12-result.json` matching the constants in `run.py`.
Provide their four matching `runNN-inputs.json` manifests, lock those filenames
in deployment `input_sha256`, and preserve the prior source-commit identities.
Run in an actual Slurm allocation, at most4CPUs:

```sh
python3 -B ROOT/source/project/experiments/legacy_metric_eval/run.py --root ROOT
```

The runner verifies old source/input hashes, exact generated five-file identity
with run12, and compiles C++17/O2/Wall/Wextra/Werror. It executes the original
numeric kernels, validation and smoke checks, then all21 full traces with at
most4 workers. Every row goes through independent `compare_audit.check` and
the same-workload/recipe U reference. Run05 is preferred for exact whole-result
comparison; run04 permits only the new `policy_study` field; run01 recursively
checks every old field and value, with no old-field deletion; run12 supplies
four further exact full-result checks. All21 rows have historical evidence.
It also exercises source/prior drift, invalid CLI and independent result
mutation refusals. These are management/timing/numeric-study checks, not native
whole-model or physical acceptance.
Copy the independently supplied `verify_completed.py` beside the runner; it
verifies the completed21case report before the runner sets its final passed flag.
Submit `sbatch --parsable job.sh` from ROOT; no positional argument is needed.
The script uses the same allocated Singularity/SystemC environment as run12,
records allocation/tool hashes, and passes Slurm job ID/CPU count into cleanenv.

Output: persistent `ROOT/results/result.json`, per-case JSON/logs, generated
files, build and original-check logs. A successful receipt requires actual
`passed=true`,21cases and `all21_historical_fields_exact=true`. The report keeps
the exact source commit, manifest/input/reference SHAs and per-case log SHA.
This directory only prepares the runner; no simulation/submission/upload was
performed here. Root owns deployment and Slurm evidence collection.
