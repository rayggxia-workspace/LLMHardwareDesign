#!/bin/bash
set -euo pipefail
test -n "${SLURM_JOB_ID:-}" || exit 2
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
run=$root/probe-g-parentabstract-v3
mkdir -p "$run"
test ! -e "$run/STARTED" || exit 2
date -Is > "$run/STARTED"
cp /public/home/yuzelu/project-circuit/yzl-cu-overlay-physical-20261116/C/config.mk "$run/config.mk"
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env CU_PROBE_CORES=8 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
run=$root/probe-g-parentabstract-v3
bash "$root/rebase-g-v9.sh" "$run" /public/home/yuzelu/project-circuit/yzl-cu-overlay-physical-20261116/C/flow/results/nangate45/c-overlay-current/base/4_cts.odb "$run/probe.odb"
export CU_PROBE_ODB=$run/probe.odb
openroad -no_init -exit "$root/pin-probe.tcl" > "$run/pin-probe.log" 2>&1
date -Is > "$run/PIN_ACCESS_PASSED"
'
