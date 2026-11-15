#!/bin/bash
#SBATCH --job-name=yzl-projection-queue
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=00:20:00
set -euo pipefail
out="${QUEUE_OUTPUT:-evidence/command-pipeline/read-queue-$SLURM_JOB_ID}"
mkdir -p "$out"
source="${QUEUE_SOURCE:-rtl/control/projection_service_cluster.sv}"
python3 tests/extract_projection_read_queue.py "$out/queue.sv" "$source"
tool=/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/tool.sh
v=/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator
bash "$tool" "$v" --binary --timing -j 4 -Wno-fatal --top-module tb_projection_read_queue --Mdir "$out/obj" tests/tb_projection_read_queue.sv "$out/queue.sv" > "$out/build.log" 2>&1
bash "$tool" "$out/obj/Vtb_projection_read_queue" | tee "$out/run.log"
sha256sum "$source" "$out/queue.sv" > "$out/source.sha256"
