#!/usr/bin/env bash
#SBATCH --job-name=mdt-280writerwave
#SBATCH --partition=v6_384
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail

if [[ ${1:-} != inside ]]; then
    bundle=${SLURM_SUBMIT_DIR:?}
    cd "$bundle"
    sha256sum --quiet -c inputs.sha256
    opt=$HOME/LLMHardware/opt
    set +u
    source /public3/soft/modules/module.sh
    module load singularity/3.7.0
    set -u
    exec srun --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
        singularity exec --cleanenv --bind "$(dirname "$bundle")" --bind "$opt" "$opt/orfs-current-repacked.rootfs" \
        bash "$bundle/run_bscc_t6_qwen3_write_span.sbatch" inside \
        "$bundle" "$SLURM_JOB_ID" "$opt" "$SLURM_CPUS_PER_TASK" "$@"
fi

source /OpenROAD-flow-scripts/env.sh
bundle=$2
root=$(dirname "$bundle")
out=$bundle/span-$3
stage=$6
mkdir "$out"
if [[ $stage == wave ]]; then
    input=$root/component-observation/replay-38782605/decode-live-w4-tile128-pr272-combined/assets/pos513-l0-descriptors.bin
    python3 -B "$bundle/prepare_qwen3_write_span.py" "$input" "$out"
    verilator=$4/verilator-5.042/bin/verilator
    "$verilator" --version > "$out/tool.txt"
    "$verilator" --binary --timing --trace --trace-depth 2 --assert -j "$5" \
        --top-module test_qwen3_write_span --Mdir "$out/obj" -Wno-TIMESCALEMOD \
        "$bundle/test_qwen3_write_span.sv" "$bundle/"{s128_kv_store_scope,s128_kv_row_transfer,s128_ddr64_store}.sv > "$out/build.log" 2>&1
    for kind in k v ffn; do
        for mode in 0 1; do
            for idle in 0 1; do
                case_dir=$out/$kind-$mode-$idle
                mkdir "$case_dir"
                "$out/obj/Vtest_qwen3_write_span" "+DESC=$out/$kind.hex" "+MODE=$mode" "+IDLE=$idle" \
                    "+WAVE=$case_dir/raw.vcd" > "$case_dir/run.log"
                grep -Fq 'PASS span ' "$case_dir/run.log"
            done
        done
    done
    cd "$out"
    sha256sum descriptors.json *.hex tool.txt */{raw.vcd,run.log} > results.sha256
else
    [[ $stage == power ]]
    wave=$bundle/span-${7:?wave job ID}
    physical=$root/write-span/physical-${8:?physical job ID}
    (cd "$wave" && sha256sum --quiet -c results.sha256)
    (cd "$physical" && sha256sum --quiet -c physical.sha256)
    netlist=$physical/flow/results/nangate45/s128_kv_store_scope/base
    export PYTHONPATH=$root/writer-power/frozen
    for path in "$wave"/*/raw.vcd; do
        case_dir=$out/$(basename "$(dirname "$path")")
        mkdir "$case_dir"
        ln -s "$path" "$case_dir/raw.vcd"
        python3 -B "$bundle/measure_c639_writeback_window.py" "$netlist" "$case_dir" \
            test_qwen3_write_span/dut 0 10450000 "$5"
    done
    cd "$out"
    sha256sum */activity.json */power/receipt.json > results.sha256
fi
sha256sum -c results.sha256
