#!/usr/bin/env bash
#SBATCH --job-name=hpy-native222
set -euo pipefail
cd "${COUPLING_TASK_ROOT:?}"
out="$PWD/job-${SLURM_JOB_ID:?}"
mkdir "$out" "$out/tmp" "$out/cache"
export TMPDIR="$out/tmp" SINGULARITY_TMPDIR="$out/tmp" SINGULARITY_CACHEDIR="$out/cache"
export SINGULARITYENV_TMPDIR="$out/tmp" SINGULARITYENV_PYTHONDONTWRITEBYTECODE=1
export SINGULARITYENV_OMP_NUM_THREADS=1 SINGULARITYENV_OPENBLAS_NUM_THREADS=1
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
  --bind /public/home/yuzelu --pwd "$PWD" "$image" \
  env PATH="/OpenROAD-flow-scripts/tools/install/OpenROAD/bin:/usr/local/bin:/usr/bin:/bin" \
  python3 -B project/experiments/m11_m12_rcx/native_snapshot.py \
  --out "$out/result" --index "${SLURM_ARRAY_TASK_ID:?}"
