#!/bin/bash
#SBATCH --job-name=yzl-sc234-pwr
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark/*) ;; *) exit 2;; esac
cd "$root"
export OMP_NUM_THREADS=10 OPENBLAS_NUM_THREADS=10 MKL_NUM_THREADS=10 PYTHONDONTWRITEBYTECODE=1
sha256sum *.py *.sbatch > input.sha256
python3 -u power_inventory.py > inventory.log 2>&1
sha256sum power-inventory.json */receipt.json */probe.log > output.sha256
