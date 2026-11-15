#!/bin/bash
#SBATCH --job-name=yzl-weight-credits
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=00:20:00
set -euo pipefail
out="evidence/command-pipeline/weight-rtl-$SLURM_JOB_ID"
mkdir -p "$out"
tool=/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/tool.sh
v=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
bash "$tool" "$v" --binary --timing -j 4 -Wno-fatal --top-module tb_weight_credits --Mdir "$out/obj" tests/tb_weight_credits.sv /public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project/rtl/w8a16_v1/weight_records.sv > "$out/build.log" 2>&1
bash "$tool" "$out/obj/Vtb_weight_credits" | tee "$out/run.log"

python3 tests/write_pipeline_receipt.py weight-rtl "$SLURM_JOB_ID"
