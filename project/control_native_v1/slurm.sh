#!/usr/bin/env bash
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
kinds=(-1 1 3 4)
kind=${kinds[${SLURM_ARRAY_TASK_ID:?}]}
bash design/run.sh "$PWD" "$PWD/results/$SLURM_ARRAY_JOB_ID-$SLURM_ARRAY_TASK_ID" "$kind"
