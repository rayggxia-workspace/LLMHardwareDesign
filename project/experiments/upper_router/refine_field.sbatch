#!/usr/bin/env bash
#SBATCH --job-name=yzl-field-refine
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --array=0-4%3
#SBATCH --time=0
set -euo pipefail
task=$1
root=$2
kind=$(python3 -c 'import sys;print(["P","U","C","F","J"][int(sys.argv[1])])' "$SLURM_ARRAY_TASK_ID")
mkdir "$task/$kind"
srun --exact --ntasks=1 --cpus-per-task=10 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu --pwd "$task/source" \
 --env OMP_NUM_THREADS=10 \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 python3 project/experiments/upper_router/refine_field.py "$root/attempt20/$kind/field" "$root/attempt23/build" "$root/attempt23/controls" "$root/attempt27/$kind" "$task/$kind/field" --threads 10
printf "%s\n" "$task/$kind/field" > "$task/$kind/selected-run.txt"
