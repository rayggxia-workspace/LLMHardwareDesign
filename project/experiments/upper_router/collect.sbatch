#!/usr/bin/env bash
#SBATCH --job-name=yzl-route-seal
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
task=$1
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores \
 python3 "$task/source/project/experiments/upper_router/collect_backend.py" \
 "$(dirname "$task")" "$task/evidence"
