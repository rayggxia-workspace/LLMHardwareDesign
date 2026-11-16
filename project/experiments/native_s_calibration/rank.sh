#!/usr/bin/env bash
set -euo pipefail
NS_AFFINITY_CSV=$(python3 -c 'import os; a=sorted(os.sched_getaffinity(0)); r=int(os.environ["SLURM_PROCID"]); assert int(os.environ["SLURM_NTASKS"])==8; assert len(a) in (12,96),a; a=a if len(a)==12 else a[r*12:(r+1)*12]; assert len(a)==12; print(",".join(map(str,a)))')
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
  --bind /public/home/yuzelu --env SLURM_PROCID="$SLURM_PROCID" \
  --env SLURM_JOB_ID="$SLURM_JOB_ID" --env NS_AFFINITY_CSV="$NS_AFFINITY_CSV" \
  --env NS_ROUND="$NS_ROUND" \
  /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif \
  python3 -B source/project/experiments/native_s_calibration/driver.py
