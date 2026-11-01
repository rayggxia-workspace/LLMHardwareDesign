#!/bin/bash
#SBATCH --job-name=yzl-rarch157-xcheck
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=0
#SBATCH --time=04:00:00
set -euo pipefail
cd "$1"
sha256sum --check FILES.sha256 > source-check.log
export PYTHONDONTWRITEBYTECODE=1
python3 project/experiments/r_architecture/crosscheck.py --out "$1/results" --corpus /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture/attempt003/results/corpus
