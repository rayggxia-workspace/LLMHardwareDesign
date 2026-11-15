#!/bin/bash
#SBATCH --job-name=yzl-dot-cache
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=00:20:00
set -euo pipefail
out="evidence/command-pipeline/dot-$SLURM_JOB_ID"
mkdir -p "$out"
tool=/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/tool.sh
v=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
for mode in 0 1; do
bash "$tool" "$v" --binary --timing -j 4 -Wno-fatal --top-module tb_dot_cache -GBAD_TAG=$mode --Mdir "$out/obj-$mode" tests/tb_dot_cache.sv rtl/services/e32_dot_service_controller.sv rtl/macros/e_s32_mac_ap64.sv rtl/macros/e_s32_mac_native.sv > "$out/build-$mode.log" 2>&1
bash "$tool" "$out/obj-$mode/Vtb_dot_cache" | tee "$out/run-$mode.log"
done

python3 tests/write_pipeline_receipt.py dot "$SLURM_JOB_ID"
