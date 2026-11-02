#!/bin/bash
#SBATCH --job-name=yzl-rarch157-cache
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=0
#SBATCH --time=03:00:00
set -euo pipefail
cd "$1"
sha256sum --check FILES.sha256 > source-check.log
export PYTHONDONTWRITEBYTECODE=1
python3 project/experiments/r_architecture/systemc_sweep.py --out "$1/results" --sweep --cache
