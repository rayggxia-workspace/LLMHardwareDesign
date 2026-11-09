#!/usr/bin/env bash
#SBATCH --job-name=mdt-rbounds
#SBATCH --partition=c64
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --array=0-3%2
#SBATCH --time=0
#SBATCH --output=slurm-%A_%a.log
set -euo pipefail
ulimit -c 0
root=$SLURM_SUBMIT_DIR
cases=(raw256 raw1024 service256 negative)
case_name=${cases[$SLURM_ARRAY_TASK_ID]}
scontrol show job "$SLURM_JOB_ID" > "$root/allocation-$case_name.txt"
sha256sum -c "$root/source.tar.sha256"
exec srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
 --env SLURM_CPUS_PER_TASK="$SLURM_CPUS_PER_TASK" --pwd "$root/source" \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 python3 -B project/experiments/r_load_bounds/run.py --case "$case_name" --out "$root/results-$case_name" \
 --old-rtl "$root/old-main/r_stream_local.sv"
