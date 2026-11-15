#!/bin/bash
#SBATCH --job-name=yzl-a-prefetch
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=00:20:00
set -euo pipefail
out="evidence/command-pipeline/a-prefetch-$SLURM_JOB_ID"
mkdir -p "$out"
tool=/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/tool.sh
v=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
for mode in 0 1 2; do
bash "$tool" "$v" --binary --timing -j 4 -Wno-fatal --top-module tb_a_frontend -GCANCEL=$mode --Mdir "$out/obj-$mode" tests/tb_a_frontend.sv rtl/services/private_a_tile_abort_frontend.sv > "$out/build-$mode.log" 2>&1
bash "$tool" "$out/obj-$mode/Vtb_a_frontend" | tee "$out/run-$mode.log"
done

python3 tests/write_pipeline_receipt.py a-prefetch "$SLURM_JOB_ID"
