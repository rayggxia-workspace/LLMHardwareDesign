#!/usr/bin/env bash
#SBATCH --job-name=yzl-feed-check
#SBATCH --partition=c96
#SBATCH --cpus-per-task=16
#SBATCH --time=12:00:00
set -euo pipefail
source_root=$1
shift
test -n "${SLURM_JOB_ID:-}"
test "$SLURM_CPUS_PER_TASK" -eq 16
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
actual=$(sha256sum "$image")
test "${actual%% *}" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
srun --ntasks=1 --cpus-per-task=16 --cpu-bind=cores \
 singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$source_root" \
 --env OMP_NUM_THREADS=16 --env OPENBLAS_NUM_THREADS=1 "$image" \
 bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; python3 "$1/project/experiments/block_feed_v1/qualify.py" "${@:2}"' \
 bash "$source_root" "$@"
