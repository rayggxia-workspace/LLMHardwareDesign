#!/usr/bin/env bash
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
repo="$PWD"
run="$repo/sim-${SLURM_JOB_ID:?}"
mkdir "$run" "$run/tmp"
export TMPDIR="$run/tmp"
verilator=${QWEN_VERILATOR:-/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator}
cd "$run"
"$verilator" --version
for profile in 0 1; do
    "$verilator" --binary --timing -Wno-fatal -j "${SLURM_CPUS_PER_TASK:?}" \
        --top-module tb_qwen_transport --Mdir "build-$profile" "-GC0_ONLY=1'b$profile" \
        "$repo"/project/rtl/qwen_transport/*.sv \
        "$repo"/project/experiments/nine_block_route/tb_qwen_transport.sv > "build-$profile.log" 2>&1
    "./build-$profile/Vtb_qwen_transport" | tee "result-$profile.log"
done
