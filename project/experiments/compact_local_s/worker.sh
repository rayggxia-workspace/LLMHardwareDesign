#!/usr/bin/env bash
set -euo pipefail
task=$1
shift
candidate=$SLURM_ARRAY_TASK_ID
cpus=$SLURM_CPUS_PER_TASK
export TMPDIR="$task/tmp-${SLURM_ARRAY_JOB_ID}-$candidate"
mkdir -p "$TMPDIR/cache" "$TMPDIR/klayout"
exec srun --exact --ntasks=1 --cpus-per-task="$cpus" --cpu-bind=cores \
  /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
  --bind /public/home/yuzelu --pwd "$task/source" \
  --env "TMPDIR=$TMPDIR,XDG_CACHE_HOME=$TMPDIR/cache,KLAYOUT_HOME=$TMPDIR/klayout,PYTHONDONTWRITEBYTECODE=1,SLURM_JOB_ID=$SLURM_JOB_ID,SLURM_CPUS_PER_TASK=$cpus,OMP_NUM_THREADS=$cpus,OPENBLAS_NUM_THREADS=1" \
  /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
  bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; exec python3 -B "$@"' bash \
  project/experiments/compact_local_s/physical.py --candidate "$candidate" \
  --generation /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation \
  --out "$task/results/$candidate" "$@"
