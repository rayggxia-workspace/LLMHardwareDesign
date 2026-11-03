#!/bin/bash
#SBATCH --job-name=hpy-s-physical
#SBATCH --partition=debug
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --time=00:30:00
set -euo pipefail
task_root="$1"
shift
export TMPDIR="$task_root/tmp-$SLURM_JOB_ID"
export XDG_CACHE_HOME="$task_root/cache-$SLURM_JOB_ID"
export PYTHONDONTWRITEBYTECODE=1
mkdir -p "$TMPDIR" "$XDG_CACHE_HOME"
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu --pwd "$task_root/source" \
 --env "TMPDIR=$TMPDIR,XDG_CACHE_HOME=$XDG_CACHE_HOME,PYTHONDONTWRITEBYTECODE=1,SLURM_JOB_ID=$SLURM_JOB_ID,OMP_NUM_THREADS=16,OPENBLAS_NUM_THREADS=1" \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; python3 -B project/experiments/block_local_s/physical.py "$@"' bash "$@"
