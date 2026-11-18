#!/usr/bin/env bash
#SBATCH --job-name=mdt-280sramwidth
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
        bash "$bundle/run_bscc_t6_qwen3_sram_width.sbatch" inside "$bundle" "$SLURM_JOB_ID" "$opt" "$SLURM_CPUS_PER_TASK"
fi
bundle=$2
root=$(dirname "$bundle")
out=$bundle/width-$3
vlt=$4/verilator-5.042/bin/verilator
rtl=$root/wide/wide-38772137/source/project/rtl/s_sram/block_feed_s16k_sram.sv
bank=$root/wide/sourcefs/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v
mkdir "$out"
"$vlt" --binary --timing --trace --trace-depth 7 --assert -j "$5" --timescale-override 1ns/1ps \
    --top-module test_qwen3_sram_banks --Mdir "$out/obj" "$bundle/test_qwen3_sram_banks.sv" "$rtl" "$bank" \
    > "$out/build.log" 2>&1
"$out/obj/Vtest_qwen3_sram_banks" "+WAVE=$out/serial.vcd" +SERIAL=1 > "$out/serial.log"
"$out/obj/Vtest_qwen3_sram_banks" "+WAVE=$out/wide-read.vcd" > "$out/wide-read.log"
grep '^PASS SRAM ' "$out"/{serial,wide-read}.log
python3 -B "$bundle/qwen3_sram_port_map.py" "$root/independent-rollup/rollup-38782605.json" "$rtl" \
    "$out/serial.log" "$out/width-map.json"
cd "$out"
sha256sum *.vcd serial.log wide-read.log width-map.json > results.sha256
sha256sum -c results.sha256
