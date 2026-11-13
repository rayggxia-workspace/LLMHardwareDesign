#!/usr/bin/env bash
set -euo pipefail
task=$1
phase=$2
shift 2
cpus=${SLURM_CPUS_PER_TASK:?}
test "$cpus" = 10 || test "$cpus" = 12
export TMPDIR="$task/tmp-$SLURM_JOB_ID"
mkdir -p "$TMPDIR/cache"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
echo "49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a  $image" | sha256sum -c
exec srun --exact --ntasks=1 --cpus-per-task="$cpus" --cpu-bind=cores \
  /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
  --bind /public/home/yuzelu --pwd "$task/source" \
  --env "TMPDIR=$TMPDIR,XDG_CACHE_HOME=$TMPDIR/cache,PYTHONDONTWRITEBYTECODE=1,SLURM_JOB_ID=$SLURM_JOB_ID,OMP_NUM_THREADS=$cpus,OPENBLAS_NUM_THREADS=1" \
  "$image" \
  bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; phase=$1; shift; exec python3 project/experiments/w8a16_physical/g_"$phase".py "$@"' bash "$phase" "$@"
