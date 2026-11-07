#!/usr/bin/env bash
#SBATCH --job-name=hpy-gds222
set -euo pipefail
cd "${COUPLING_TASK_ROOT:?}"
out="$PWD/job-${SLURM_JOB_ID:?}"
mkdir "$out" "$out/tmp" "$out/cache"
export TMPDIR="$out/tmp" SINGULARITY_TMPDIR="$out/tmp" SINGULARITY_CACHEDIR="$out/cache"
export SINGULARITYENV_TMPDIR="$out/tmp" SINGULARITYENV_PYTHONDONTWRITEBYTECODE=1
export SINGULARITYENV_QT_QPA_PLATFORM=offscreen
export SINGULARITYENV_COUPLING_TOPOLOGY_OUT="$out/result"
export SINGULARITYENV_COUPLING_TOPOLOGY_INDEX="${SLURM_ARRAY_TASK_ID:?}"
export SINGULARITYENV_COUPLING_THREADS="${SLURM_CPUS_PER_TASK:?}"
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
  --bind /public/home/yuzelu --pwd "$PWD" \
  /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
  klayout -b -r project/experiments/m11_m12_rcx/native_topology.py
