#!/bin/bash
#SBATCH --job-name=yzl-sc234-old
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark/*) ;; *) exit 2;; esac
cd "$root"
prefix=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153/install
export LD_LIBRARY_PATH="$prefix/lib64:${LD_LIBRARY_PATH:-}"
export OMP_NUM_THREADS=10 OPENBLAS_NUM_THREADS=10 MKL_NUM_THREADS=10 PYTHONDONTWRITEBYTECODE=1
sha256sum *.cpp *.py "$prefix"/lib64/libsystemc.so.3.0.1 > input.sha256
g++ --version > versions.log
g++ -std=c++17 -O2 -Wall -Wextra -Werror -I"$prefix/include" timed_resources.cpp -L"$prefix/lib64" -lsystemc -pthread -o timed-resources > build.log 2>&1
python3 -u run_baselines.py /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/algorithm-fix-220-statecost-v2-plan/generated results > baseline.log 2>&1
sha256sum results/summary.json timed-resources baseline.log > output.sha256
