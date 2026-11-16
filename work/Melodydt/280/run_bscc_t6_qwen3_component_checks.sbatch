#!/usr/bin/env bash
#SBATCH --job-name=mdt-280componentcheck
#SBATCH --partition=v6_384
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
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
        bash "$bundle/run_bscc_t6_qwen3_component_checks.sbatch" inside "$bundle" "$SLURM_JOB_ID" "$opt"
fi

bundle=$2
root=$(dirname "$bundle")
out=$bundle/check-$3
vlt=$4/verilator-5.042/bin/verilator
project=$root/wide/wide-38772137/source/project
assets=$root/component-observation/replay-38782605/decode-live-w4-tile128-pr272-combined/assets
bank=$root/wide/sourcefs/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v
mkdir "$out"
python3 -B "$bundle/prepare_qwen3_component_checks.py" "$project" "$assets" "$out"
"$vlt" --version > "$out/tool.txt"
compile() {
    local top=$1
    shift
    "$vlt" --binary --timing --trace --trace-depth 5 --assert -j 4 --timescale-override 1ns/1ps \
        --top-module "$top" --Mdir "$out/obj-$top" "$@" > "$out/build-$top.log" 2>&1
}
sram() {
    local top=test_qwen3_sram_banks
    compile "$top" "$bundle/$top.sv" "$project/rtl/s_sram/block_feed_s16k_sram.sv" "$bank"
    "$out/obj-$top/V$top" "+WAVE=$out/sram.vcd" > "$out/sram.log"
    grep '^PASS SRAM ' "$out/sram.log"
}
pm() {
    local top=test_qwen3_pm_stream
    compile "$top" "$bundle/$top.sv" "$project/rtl/mother_control_native/native_pm_image_stream.sv"
    for size in 352 1664; do
        for mode in 0 1; do
            "$out/obj-$top/V$top" "+BYTES=$size" "+MODE=$mode" "+IMAGE=$out/pm-$size.hex" \
                "+WAVE=$out/pm-$size-$mode.vcd" > "$out/pm-$size-$mode.log"
            grep '^PASS PM ' "$out/pm-$size-$mode.log"
        done
    done
}
u_residual() {
    local top=test_native_add_scope
    compile "$top" "$out/$top.sv" "$project/rtl/block_local_native/"{s32_add_scope,projection_bias_e32_s128}.sv \
        "$project/rtl/w8a16_v1/"{e_s32_ap64,e_s32_native}.sv "$project/rtl/s_sram/"{local_s_base,block_feed_s16k_sram}.sv \
        "$project/experiments/shared_x_control/rtl/native_s128_mux3.sv" "$bank"
    "$out/obj-$top/V$top" "+DESCRIPTORS=$out/add.hex" "+WAVE=$out/add.vcd" > "$out/add.log"
    grep '^PASS native ADD2 ' "$out/add.log"
}
pids=()
for test in sram pm u_residual; do
    ("$test") &
    pids+=("$!")
done
failed=0
for pid in "${pids[@]}"; do wait "$pid" || failed=1; done
((failed==0))
cd "$out"
sha256sum inputs.json tool.txt *.hex *.vcd sram.log pm-*.log add.log > results.sha256
sha256sum -c results.sha256
