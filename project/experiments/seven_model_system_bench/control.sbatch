#!/bin/bash
#SBATCH --job-name=hpy-seven-ctrl
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --cpus-per-task=8
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/PingyangHuang/issue-197-*) ;; *) exit 2;; esac
cd "$root"
sha256sum -c control-upload.sha256
mkdir source-control control-tmp
tar -xf control-source.tar -C source-control
export SINGULARITYENV_TMPDIR="$root/control-tmp"
export SINGULARITYENV_XDG_CACHE_HOME="$root/control-tmp"
export SINGULARITYENV_PYTHONDONTWRITEBYTECODE=1
export SINGULARITYENV_SLURM_JOB_ID="$SLURM_JOB_ID"
srun --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
    --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif \
    python3 -B "$root/source-control/project/experiments/control_v1/run.py" \
    --model system --verify-only --out "$root/control-results"
