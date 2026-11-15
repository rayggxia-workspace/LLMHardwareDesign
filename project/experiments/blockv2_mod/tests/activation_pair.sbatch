#!/bin/bash
#SBATCH --job-name=yzl-activation-pair
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=00:20:00
set -euo pipefail
out="evidence/command-pipeline/activation-pair-$SLURM_JOB_ID"
mkdir -p "$out"
tool=/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/tool.sh
v=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
for mode in normal; do
args=(); if [ "$mode" = read_error ]; then args=(-GERROR_READ=1); fi; if [ "$mode" = ack_error ]; then args=(-GERROR_ACK=1); fi
bash "$tool" "$v" --binary --timing -j 4 -Wno-fatal --top-module tb_activation_pair "${args[@]}" --Mdir "$out/obj-$mode" tests/tb_activation_pair.sv rtl/p_services/s128_ddr_range_load.sv > "$out/build-$mode.log" 2>&1
bash "$tool" "$out/obj-$mode/Vtb_activation_pair" | tee "$out/run-$mode.log"

done
