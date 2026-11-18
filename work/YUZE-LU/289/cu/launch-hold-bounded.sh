#!/bin/bash
set -euo pipefail
test -n "${SLURM_JOB_ID:-}" || { echo 'Compute allocation required'; exit 2; }
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env "OMP_NUM_THREADS=${3:-8}" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash "$root/run-hold-bounded.sh" "$@"
