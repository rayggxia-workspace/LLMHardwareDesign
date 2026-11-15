#!/bin/bash
#SBATCH --job-name=yzl-shared-read-window
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=00:20:00
set -euo pipefail
out="evidence/command-pipeline/shared-read-$SLURM_JOB_ID";mkdir -p "$out"
tool=/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/tool.sh
v=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
ext=/public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project/rtl/mother_control_native
bash "$tool" "$v" --binary --timing -j 4 -Wno-fatal --top-module tb_shared_read_window --Mdir "$out/obj" -y "$ext" -y rtl/control tests/tb_shared_read_window.sv rtl/control/native_shared_memory_plane.sv > "$out/build.log" 2>&1
bash "$tool" "$out/obj/Vtb_shared_read_window" | tee "$out/run.log"
