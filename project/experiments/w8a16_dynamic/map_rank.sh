#!/usr/bin/env bash
set -euo pipefail
root=$1
top=$2
allowed=$(python3 -c 'import os;print(",".join(str(v) for v in sorted(os.sched_getaffinity(0))))')
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu --env "SLURM_JOB_ID=$SLURM_JOB_ID,PYTHONDONTWRITEBYTECODE=1,OMP_NUM_THREADS=10" \
 "$image" taskset -c "$allowed" python3 -B "$root/source/project/experiments/w8a16_dynamic/map.py" \
 --proof "$DYNAMIC_PROOF" --out "$root/map-$top" --top "$top"
