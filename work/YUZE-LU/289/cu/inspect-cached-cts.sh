#!/bin/bash
set -euo pipefail
test -n "${SLURM_JOB_ID:-}" || exit 2
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
run=$root/runs/C-v16-genericadder-cached
out=$run/cts-diagnostic
mkdir -p "$out"
libs=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$run/config.mk" | tail -1)
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env "CU_LIBS=$libs,CU_RESULTS=$run/flow/results/nangate45/c-overlay-current/base,CU_OUT=$out" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "$root/inspect-cached-cts.tcl"
