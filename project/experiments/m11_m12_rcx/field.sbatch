#!/usr/bin/env bash
#SBATCH --job-name=hpy-upper-field
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
mkdir -p "$PWD/tmp" "$PWD/cache"
export TMPDIR="$PWD/tmp" SINGULARITY_TMPDIR="$PWD/tmp" SINGULARITY_CACHEDIR="$PWD/cache"
export SINGULARITYENV_TMPDIR="$PWD/tmp" SINGULARITYENV_PYTHONDONTWRITEBYTECODE=1
export SINGULARITYENV_OMP_NUM_THREADS=1 SINGULARITYENV_OPENBLAS_NUM_THREADS=1
export SINGULARITYENV_SLURM_CPUS_PER_TASK="${SLURM_CPUS_PER_TASK:?}"
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
printf '49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a  %s\n' "$image" | sha256sum -c -
exec singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$PWD" "$image" \
    bash project/experiments/m11_m12_rcx/field_worker.sh "job-${SLURM_JOB_ID:?}" "$@"
