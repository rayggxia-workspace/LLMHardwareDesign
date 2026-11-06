#!/usr/bin/env bash
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
repo="$PWD"
top="${1:?pass the top module}"
size="${2:?pass the square die size in um}"
run="$repo/run-${SLURM_JOB_ID:?}-$top"
mkdir "$run" "$run/tmp"
export TMPDIR="$run/tmp"
runtime=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv
    --bind /public/home/yuzelu
    --env "SLURM_CPUS_PER_TASK=${SLURM_CPUS_PER_TASK:?},TMPDIR=$TMPDIR,QT_QPA_PLATFORM=offscreen,OPENBLAS_NUM_THREADS=1"
    /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif)
"${runtime[@]}" bash -c '
    set -euo pipefail
    source /OpenROAD-flow-scripts/env.sh
    python3 -B "$1/project/experiments/nine_block_route/physical_switch.py" "$2" "$3/native" --size "$4"
' _ "$repo" "$top" "$run" "$size"
