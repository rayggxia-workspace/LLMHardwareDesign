#!/usr/bin/env bash
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
repo="$PWD"
run="$repo/sim-${SLURM_JOB_ID:?}"
mkdir "$run" "$run/tmp"
runtime=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv
    --bind /public/home/yuzelu
    --env "SLURM_CPUS_PER_TASK=${SLURM_CPUS_PER_TASK:?},TMPDIR=$run/tmp"
    /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif)
"${runtime[@]}" bash -c '
    set -euo pipefail
    source /OpenROAD-flow-scripts/env.sh
    repo=$1
    cd "$2"
    verilator --version
    for profile in 0 1; do
        verilator --binary --timing -Wno-fatal -j "$SLURM_CPUS_PER_TASK" \
            --top-module tb_qwen_transport --Mdir "build-$profile" -GC0_ONLY="$profile" \
            "$repo"/project/rtl/qwen_transport/*.sv \
            "$repo"/project/experiments/nine_block_route/tb_qwen_transport.sv > "build-$profile.log" 2>&1
        "./build-$profile/Vtb_qwen_transport" | tee "result-$profile.log"
    done
' _ "$repo" "$run"
