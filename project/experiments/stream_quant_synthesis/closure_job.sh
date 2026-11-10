#!/usr/bin/env bash
#SBATCH --job-name=yl-sq-closure
#SBATCH --partition=c64,c96
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=0
#SBATCH --output=closure-slurm-%j.log
set -euo pipefail
root=$SLURM_SUBMIT_DIR
cd "$root/source"
sha256sum -c "$root/source-files.sha256" > "$root/source-check.log"
cd "$root"
scontrol show job "$SLURM_JOB_ID" > allocation.txt
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
exec srun --exact -n1 -c4 --cpu-bind=cores python3 -B \
 "$root/source/project/experiments/stream_quant_synthesis/closure.py" --root "$root"
