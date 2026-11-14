#!/usr/bin/env bash
set -euo pipefail
root=$1
rows=$2
top=$3
allowed=$(python3 -c 'import os;print(",".join(str(x) for x in sorted(os.sched_getaffinity(0))))')
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu --env "SLURM_JOB_ID=$SLURM_JOB_ID,PYTHONDONTWRITEBYTECODE=1,OMP_NUM_THREADS=10" \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif taskset -c "$allowed" \
 python3 -B "$root/source/project/experiments/native_s32_dot/map_native.py" \
 --source "$root/source" --proof "$NATIVE32_PROOF" --rows "$rows" --top "$top" --out "$root/map-$top-$rows"
