#!/usr/bin/env bash
set -euo pipefail
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
expected=49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
sha256sum "$image" > image.sha256
read -r actual _ < image.sha256
test "$actual" = "$expected"
source_root=$1
mode=$2
singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$PWD" \
  --env OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK" --env OPENBLAS_NUM_THREADS=1 \
  --env SLURM_JOB_ID="$SLURM_JOB_ID" --env SLURM_CPUS_PER_TASK="$SLURM_CPUS_PER_TASK" \
  "$image" bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; python3 "$1/project/experiments/block_v1/worker.py" "$1" "$2" "$3"' \
  bash "$source_root" "$mode" "$SLURM_CPUS_PER_TASK"
