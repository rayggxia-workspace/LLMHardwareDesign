#!/usr/bin/env bash
#SBATCH --job-name=yzl-field-collect
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
task=$1;scene=$2;shards=$3
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$task/source" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif python3 project/experiments/upper_router/collect_field.py "$scene" "$task/field" "$shards/shard-0/selected" "$shards/shard-1/selected" "$shards/shard-2/selected" "$shards/shard-3/selected" "$shards/shard-4/selected"
