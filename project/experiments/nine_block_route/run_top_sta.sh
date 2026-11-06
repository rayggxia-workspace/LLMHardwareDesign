#!/usr/bin/env bash
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
base="$PWD"
run="timing-${SLURM_JOB_ID:?}"
v="${1:?}"
shift
python3 top_sta.py "$base" "$run" "$@"
cd "$run"
runtime=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif)
"${runtime[@]}" bash -c 'source /OpenROAD-flow-scripts/env.sh; exec openroad -no_init -exit "$1"' _ "$PWD/sta-$v.tcl" > "timing-$v.log" 2>&1
