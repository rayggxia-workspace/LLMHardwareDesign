#!/usr/bin/env bash
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
repo="$PWD"
run="$repo/sim-${SLURM_JOB_ID:?}"
mkdir "$run" "$run/tmp"
export TMPDIR="$run/tmp"
verilator=${QWEN_VERILATOR:-/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator}
runtime=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv
    --bind /public/home/yuzelu --env "TMPDIR=$TMPDIR"
    /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif)
"${runtime[@]}" bash -s -- "$repo" "$run" "$verilator" "${SLURM_CPUS_PER_TASK:?}" "$@" <<'BASH'
set -euo pipefail
repo=$1
cd "$2"
verilator=$3
"$verilator" --version
sources=("$repo"/project/rtl/qwen_transport/*.sv)
if [[ -n "${5:-}" ]]; then
    source /OpenROAD-flow-scripts/env.sh
    yosys -Q -p 'read_liberty -ignore_miss_func -ignore_miss_dir /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib; write_verilog -noattr cells.v' > cells.log
    sources=(cells.v "$5" "${6:?pass both routed netlists}")
    sha256sum "$5" "$6" > netlists.sha256
fi
for profile in 0 1; do
    "$verilator" --binary --timing -Wno-fatal -j "$4" \
        --top-module tb_qwen_transport --Mdir "build-$profile" "-GC0_ONLY=1'b$profile" \
        "${sources[@]}" \
        "$repo"/project/experiments/nine_block_route/tb_qwen_transport.sv > "build-$profile.log" 2>&1
    "./build-$profile/Vtb_qwen_transport" | tee "result-$profile.log"
done
BASH
