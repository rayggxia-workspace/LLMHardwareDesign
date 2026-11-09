#!/usr/bin/env bash
#SBATCH --job-name=mdt-elastic
#SBATCH --partition=c64,c96
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail
ulimit -c 0
root=$SLURM_SUBMIT_DIR
cd "$root/source"
sha256sum -c "$root/source-files.sha256"
scontrol show job "$SLURM_JOB_ID" > "$root/allocation.txt"
image=/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif
sha256sum "$image" > "$root/tools.sha256"
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
exec srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
 --env SLURM_CPUS_PER_TASK="$SLURM_CPUS_PER_TASK" "$image" \
 python3 -B project/experiments/area_speed_study/elastic/run_elastic.py \
 --repo "$root/source" --out "$root/results" --workers "$SLURM_CPUS_PER_TASK" \
 --stage1-result "$root/stage1-result.json"
