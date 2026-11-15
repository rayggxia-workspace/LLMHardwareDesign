#!/bin/bash
#SBATCH --job-name=yzl-read-window
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=00:20:00
set -euo pipefail
out="evidence/command-pipeline/read-window-$SLURM_JOB_ID";mkdir -p "$out"
tool=/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/tool.sh
v=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
bash "$tool" "$v" --binary --timing -j 4 -Wno-fatal --top-module tb_native64_read_window --Mdir "$out/obj" tests/tb_native64_read_window.sv rtl/control/native64_dma_read_window_client.sv > "$out/build.log" 2>&1
bash "$tool" "$out/obj/Vtb_native64_read_window" | tee "$out/run.log"
