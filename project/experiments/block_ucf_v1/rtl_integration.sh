#!/usr/bin/env bash
#SBATCH --job-name=yzl-ucf-rtl
#SBATCH --partition=debug
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:20:00
#SBATCH --output=rtl-%j.log
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
export LC_ALL=C
runtime=(/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu
    /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif)
verilator=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
bank=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45.v
echo "6c1c1ca9d183ab7c4c74df056c9730cf352d165301546126e29b644a45ef9de7  $bank" | sha256sum -c
sha256sum ./*.sv
"${runtime[@]}" "$verilator" --binary --timing --assert --timescale-override 1ns/1ns \
    --top-module tb_block_ucf16 -j "${SLURM_CPUS_PER_TASK}" --Mdir "obj-${SLURM_JOB_ID}" \
    -I. native_r.vlt ./*.sv "$bank"
"${runtime[@]}" "./obj-${SLURM_JOB_ID}/Vtb_block_ucf16"
