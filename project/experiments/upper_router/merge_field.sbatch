#!/usr/bin/env bash
#SBATCH --job-name=yzl-field-merge
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
task=$1
partitions=$2
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu --pwd "$task/source" \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 python3 project/experiments/upper_router/merge_field_context.py "$task/field" \
 "$partitions/shard-0/field" "$partitions/shard-1/field" "$partitions/shard-2/field" "$partitions/shard-3/field" "$partitions/shard-4/field"
