#!/bin/bash
#SBATCH --job-name=yzl-activation-scope
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=00:20:00
set -euo pipefail
out="evidence/command-pipeline/activation-scope-$SLURM_JOB_ID"
mkdir -p "$out"
tool=/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/tool.sh
v=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
for bytes in 512 8192; do
bash "$tool" "$v" --binary --timing -j 4 -Wno-fatal --top-module tb_activation_scope -GBYTES=$bytes --Mdir "$out/obj-$bytes" tests/tb_activation_scope.sv rtl/p_services/ddr_s128_load_scope.sv rtl/p_services/s128_ddr_range_load.sv > "$out/build-$bytes.log" 2>&1
bash "$tool" "$out/obj-$bytes/Vtb_activation_scope" | tee "$out/run-$bytes.log"
done
