# Default compatibility and cold-reset regression

This entry runs separately from the shared32 native experiment. It does not
edit the original `p_native_opt` or `pu_leaf_base` benches, or the original
three RTL modules captured in `compat_baseline/`.

The baseline snapshots identify upstream commit
`a8e793e4c6f97e9dca5b0cc203797dcd3b0e0e78` and local baseline prefix
`160a3de`. Their Windows checkout hashes and LF-normalized snapshot hashes
are recorded separately in `compat_baseline/source.json`. Only CRLF→LF
conversion is applied to those copies. All other common RTL dependencies
come from the same deployed source and are listed with hashes in the result.

`compat_generate.py` makes two derived copies of each original bench. Both
copies receive the same read-only event observer. Only the candidate copy
ties the new shared/cold/wide-write ports explicitly inactive. The original
assertions, program, expected numerical results, and measurement statements
are retained. The four paired configurations are:

- `tb_popt_group`: OPT=0, BANK_RW=0, SEGMENTS=2;
- `tb_pu_p_group`: the original full P program, including errors, writeback,
  M→G routing and reset;
- `tb_popt_local`: BANK_RW=0, REUSE_A=0, HOLD_CYCLES=0 and 32, including
  loader data/order, bounds, reset, and the old rows=0 rejection contract.

Each pair is run with the existing three initialization cases (mode1/143,
mode2/143, mode2/144). The checker requires exact equality of every observed
handshake's cycle and data, plus all original METRIC/PASS receipts. It saves
both full logs and normalized event files. This provides twelve paired
comparisons; it does not substitute a newly invented expected latency.

`compat_cold_local.sv` separately uses TRUE_RW=1, SHARED_A=0, REUSE_A=0. It
checks cold reset with an outstanding SRAM read and held feeder data, then
rewrites and verifies fresh data. Warm reset must cancel the feeder and
preserve migrated memory. It directly checks that the legacy loader branch
has no remaining pending/busy state after either reset. This case runs with
the same three initialization modes/seeds.

Prepare a fresh authorized Slurm run directory with `source/`, the normal
SHA-bound `inputs.json`, and `compat_job.sh` copied as its job script:

```
sbatch --parsable compat_job.sh
python3 -B source/project/experiments/shared32_native/compat_run.py --root RUN
```

The Python entry rejects execution without 1–4 allocated Slurm CPUs and
checks the actual pre-existing SRAM model SHA. Every used RTL source,
included G table, original bench, generator/runner, cold bench, job and
baseline snapshot must be present in the source SHA manifest. The job saves
the Slurm allocation and tool-image/binary hashes and uses the same ORFS
container as the primary native experiment.

Builds have a 240-second timeout and other commands a 60-second timeout.
On timeout the runner kills the complete process group, preserves captured
output and records the timeout before failing. The original legacy Verilator
warning policy is retained, but candidate PINMISSING/PINNOTFOUND diagnostics
must be a subset of those in its original-source build. The cold bench must
have neither diagnostic. Strict new-module lint remains part of the separate
shared32 primary run. No EDA is intended on the local computer.

Success is `SHARED32_COMPAT_PASS exact_default_pairs=12 cold_reset_runs=3`
and `results/result.json` with `passed=true`. New physical timing, whole-model
token/s and full-model numerical qualification are outside this regression.
