#!/usr/bin/env bash
#SBATCH --job-name=hpy-timing222
set -euo pipefail
cd "${TIMING_TASK_ROOT:?}"
out="$PWD/job-${SLURM_JOB_ID:?}-${SLURM_ARRAY_TASK_ID:-0}"
mkdir "$out" "$out/tmp" "$out/cache"
export TMPDIR="$out/tmp" SINGULARITY_TMPDIR="$out/tmp" SINGULARITY_CACHEDIR="$out/cache"
export SINGULARITYENV_TMPDIR="$out/tmp" SINGULARITYENV_PYTHONDONTWRITEBYTECODE=1
export SINGULARITYENV_TIMING_OUT="$out" SINGULARITYENV_TIMING_CPUS="${SLURM_CPUS_PER_TASK:?}"
export SINGULARITYENV_TIMING_INDEX="${SLURM_ARRAY_TASK_ID:-0}"
export SINGULARITYENV_PATH="/OpenROAD-flow-scripts/tools/install/OpenROAD/bin:/usr/local/bin:/usr/bin:/bin"
export SINGULARITYENV_OMP_NUM_THREADS=1 SINGULARITYENV_OPENBLAS_NUM_THREADS=1
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$PWD" \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 python3 -B "$TIMING_TASK_ROOT/project/experiments/m11_m12_rcx/$1" "${@:2}"
