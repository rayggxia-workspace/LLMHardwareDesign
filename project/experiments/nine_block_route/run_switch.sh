#!/usr/bin/env bash
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
repo="$PWD"
top="${1:?pass the top module}"
size="${2:?pass the square die size in um}"
pin_plan=()
if [[ -n "${3:-}" ]]; then pin_plan=(--pin-plan "$3"); fi
run="$repo/run-${SLURM_JOB_ID:?}-$top"
mkdir "$run" "$run/tmp"
export TMPDIR="$run/tmp"
runtime=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv
    --bind /public/home/yuzelu
    --env "SLURM_CPUS_PER_TASK=${SLURM_CPUS_PER_TASK:?},TMPDIR=$TMPDIR,QT_QPA_PLATFORM=offscreen,OPENBLAS_NUM_THREADS=1"
    --env "QWEN_PIN_LAYOUT=${QWEN_PIN_LAYOUT:-edge},QWEN_INPUT_PROTECTION=${QWEN_INPUT_PROTECTION:-0}"
    /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif)
"${runtime[@]}" bash -c '
    set -euo pipefail
    source /OpenROAD-flow-scripts/env.sh
    repo=$1; top=$2; run=$3; size=$4; shift 4
    python3 -B "$repo/project/experiments/nine_block_route/physical_switch.py" "$top" "$run/native" --size "$size" "$@"
' _ "$repo" "$top" "$run" "$size" "${pin_plan[@]}"
