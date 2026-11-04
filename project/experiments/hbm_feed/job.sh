#!/bin/bash
#SBATCH --job-name=hpy-hbm181
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=0
set -euo pipefail
task_root="$1"
source_root="$task_root/source"
export TMPDIR="$task_root/tmp"
export XDG_CACHE_HOME="$task_root/cache"
export PYTHONDONTWRITEBYTECODE=1
mkdir -p "$TMPDIR" "$XDG_CACHE_HOME"
cd "$source_root"
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu --pwd "$source_root" \
 --env "TMPDIR=$TMPDIR,XDG_CACHE_HOME=$XDG_CACHE_HOME,PYTHONDONTWRITEBYTECODE=1,SLURM_JOB_ID=$SLURM_JOB_ID" \
 /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif \
 python3 -B project/experiments/hbm_feed/run_server.py --out "$task_root/result"
