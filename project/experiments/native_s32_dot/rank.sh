#!/usr/bin/env bash
set -euo pipefail
root=$1
seed=$2
check=${NATIVE32_CHECK:-check.py}
case "$check" in check.py|check_s128.py|check_stage64.py) ;; *) exit 2;; esac
allowed=$(python3 -c 'import os;print(",".join(str(x) for x in sorted(os.sched_getaffinity(0))))')
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu --env "SLURM_JOB_ID=$SLURM_JOB_ID,PYTHONDONTWRITEBYTECODE=1,OMP_NUM_THREADS=10" \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif taskset -c "$allowed" \
 python3 -B "$root/source/project/experiments/native_s32_dot/$check" \
 --source "$root/source" --out "$root/seed-$seed" --seed "$seed"
