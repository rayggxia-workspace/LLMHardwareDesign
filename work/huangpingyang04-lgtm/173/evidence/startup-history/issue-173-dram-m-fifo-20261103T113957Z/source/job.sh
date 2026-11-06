#!/bin/bash
#SBATCH --job-name=hpy-dm173
set -eu
task_root=/public/home/yuzelu/PingyangHuang/issue-173-dram-m-fifo-20261103T113957Z
export TMPDIR="$task_root/tmp" XDG_CACHE_HOME="$task_root/cache" PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1
mkdir -p "$TMPDIR" "$XDG_CACHE_HOME"
cd "$task_root/source"
python3 -B project/experiments/dram_m_fifo/run.py --verilator /public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator --jobs 8 --out "$task_root/results"
