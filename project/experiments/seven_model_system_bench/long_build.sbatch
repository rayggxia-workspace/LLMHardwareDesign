#!/bin/bash
#SBATCH --job-name=hpy-long-build
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --cpus-per-task=4
#SBATCH --time=01:00:00
set -euo pipefail
root=$(realpath "$1")
short=$(realpath "$2")
systemc=$(realpath "$3")
case "$root" in /public/home/yuzelu/PingyangHuang/issue-197-long-*) ;; *) exit 2;; esac
cd "$root"
sha256sum -c build-upload.sha256
mkdir "$root/build-tmp" "$root/observed-source"
export TMPDIR="$root/build-tmp" XDG_CACHE_HOME="$root/build-tmp"
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
baseline_sha=$(awk '$2=="systemc-source.tar" {print $1}' "$short/systemc-upload.sha256")
printf '%s  %s\n' "$baseline_sha" "$short/systemc-source.tar" | sha256sum -c
tar -xf "$short/systemc-source.tar" -C "$root/observed-source"
python3 -B instrument_long.py "$root/observed-source/project/systemc"
python3 -B "$root/observed-source/project/systemc/llm_cd/run.py" --systemc-prefix "$systemc" \
    --out "$root/long-build" --save-evidence "$root/long-build-evidence" --no-sanitize >build-long.log
sha256sum -- long-build/build/llm_cd_bench long-build/receipt.json \
    observed-source/project/systemc/llm/llm_bench.cpp \
    observed-source/project/systemc/llm/tensor_link.hpp >observed-build.sha256
