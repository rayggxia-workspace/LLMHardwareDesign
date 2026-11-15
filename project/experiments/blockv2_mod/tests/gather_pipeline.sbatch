#!/bin/bash
#SBATCH --job-name=yzl-gather-pipe
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=00:20:00
set -euo pipefail
out="evidence/command-pipeline/gather-$SLURM_JOB_ID"
mkdir -p "$out"
tool=/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/tool.sh
v=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
for mode in normal read_error ack_error cancel cancel_writes bad_index index_badtag index_cancel; do
args=(); if [ "$mode" = index_badtag ]; then args=(-GINDEX_BADTAG=1); fi; if [ "$mode" = index_cancel ]; then args=(-GINDEX_CANCEL=1); fi; if [ "$mode" = bad_index ]; then args=(-GBAD_INDEX=1); fi; if [ "$mode" = cancel_writes ]; then args=(-GCANCEL=2); fi; if [ "$mode" = cancel ]; then args=(-GCANCEL=1); fi; if [ "$mode" = read_error ]; then args=(-GERROR_READ=1); fi; if [ "$mode" = ack_error ]; then args=(-GERROR_ACK=1); fi
bash "$tool" "$v" --binary --timing -j 4 -Wno-fatal --top-module tb_gather_pipeline "${args[@]}" --Mdir "$out/obj-$mode" tests/tb_gather_pipeline.sv rtl/p_services/s128_ddr_range_load.sv rtl/services/indexed_gather_service_controller.sv > "$out/build-$mode.log" 2>&1
bash "$tool" "$out/obj-$mode/Vtb_gather_pipeline" | tee "$out/run-$mode.log"

done
