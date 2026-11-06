#!/bin/bash
#SBATCH --job-name=hpy-seven-sc
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --cpus-per-task=8
set -euo pipefail
root=$(realpath "$1")
inputs=$(realpath "$2")
systemc=$(realpath "$3")
case "$root" in /public/home/yuzelu/PingyangHuang/issue-197-*) ;; *) exit 2;; esac
cd "$root"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
mkdir "$root/tmp"
export TMPDIR="$root/tmp" XDG_CACHE_HOME="$root/cache"
awk '/MemAvailable/ {print; if ($2 < 120*1024*1024) exit 1}' /proc/meminfo
sha256sum -c systemc-upload.sha256
mkdir source-systemc
tar -xf systemc-source.tar -C source-systemc
python3 -B source-systemc/project/systemc/llm_cd/run.py --systemc-prefix "$systemc" \
    --out "$root/cd-build" --save-evidence "$root/cd-build-evidence" --no-sanitize >build-systemc.log
python3 -B run_systemc.py "$root/source-systemc" "$root/cd-build/build/llm_cd_bench" \
    "$root/frozen-systemc.json" "$inputs" "$root/systemc-results"
