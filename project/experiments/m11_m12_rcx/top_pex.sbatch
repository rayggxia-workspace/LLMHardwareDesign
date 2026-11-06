#!/usr/bin/env bash
#SBATCH --job-name=hpy-top-pex
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
out="$PWD/job-${SLURM_JOB_ID:?}"
mkdir "$out" "$out/tmp" "$out/cache"
export TMPDIR="$out/tmp" SINGULARITY_TMPDIR="$out/tmp" SINGULARITY_CACHEDIR="$out/cache"
export SINGULARITYENV_TMPDIR="$out/tmp" SINGULARITYENV_PYTHONDONTWRITEBYTECODE=1
export SINGULARITYENV_OMP_NUM_THREADS=1 SINGULARITYENV_OPENBLAS_NUM_THREADS=1
export SINGULARITYENV_SLURM_CPUS_PER_TASK="${SLURM_CPUS_PER_TASK:?}"
export SINGULARITYENV_PEX_SHARD="${SLURM_ARRAY_TASK_ID:-0}"
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
printf '49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a  %s\n' "$image" | sha256sum -c -
stage=$1
shift
exec singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$PWD" "$image" \
    env PATH="/OpenROAD-flow-scripts/tools/install/OpenROAD/bin:/usr/local/bin:/usr/bin:/bin" \
    python3 -B "project/experiments/m11_m12_rcx/top_$stage.py" --out "$out/result" "$@"
