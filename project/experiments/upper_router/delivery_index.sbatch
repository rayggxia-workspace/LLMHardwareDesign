#!/usr/bin/env bash
#SBATCH --job-name=yzl-route-index
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
task=$1;delivery=$2;shift 2
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu --pwd "$task/source" --env OMP_NUM_THREADS=10 \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 python3 project/experiments/upper_router/delivery_index.py \
 "$delivery" "$task/delivery-index.json" "$@"
