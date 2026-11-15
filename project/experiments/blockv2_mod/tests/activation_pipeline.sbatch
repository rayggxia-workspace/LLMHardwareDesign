#!/bin/bash
#SBATCH --job-name=yzl-activation-pipe
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=00:20:00
set -euo pipefail
out="evidence/command-pipeline/activation-$SLURM_JOB_ID"
mkdir -p "$out"
tool=/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/tool.sh
v=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
for mode in normal read_error ack_error cancel cancel_writes cancel_held_read cancel_held_write error_held_read error_held_write bad_ack; do
args=()
if [ "$mode" = bad_ack ]; then args=(-GBAD_ACK=1); fi
if [ "$mode" = cancel_held_read ]; then args=(-GCANCEL=3 -GHOLD_READ=1); fi
if [ "$mode" = cancel_held_write ]; then args=(-GCANCEL=4 -GHOLD_WRITE=1); fi
if [ "$mode" = error_held_read ]; then args=(-GERROR_READ=1 -GHOLD_READ=1); fi
if [ "$mode" = error_held_write ]; then args=(-GERROR_READ=1 -GHOLD_WRITE=1); fi
 if [ "$mode" = cancel_writes ]; then args=(-GCANCEL=2); fi; if [ "$mode" = cancel ]; then args=(-GCANCEL=1); fi; if [ "$mode" = read_error ]; then args=(-GERROR_READ=1); fi; if [ "$mode" = ack_error ]; then args=(-GERROR_ACK=1); fi
bash "$tool" "$v" --binary --timing -j 4 -Wno-fatal --top-module tb_activation_pipeline "${args[@]}" --Mdir "$out/obj-$mode" tests/tb_activation_pipeline.sv rtl/p_services/s128_ddr_range_load.sv > "$out/build-$mode.log" 2>&1
bash "$tool" "$out/obj-$mode/Vtb_activation_pipeline" | tee "$out/run-$mode.log"

done
