#!/usr/bin/env bash
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
src="${1:?path to the trial scripts}"
id="${SLURM_ARRAY_TASK_ID:?}"
gaps=(96 128 192)
seed=$((id % 8))
export LLHD_COMPACT_U="${gaps[$((id / 8))]}"
export SLURM_ARRAY_JOB_ID="${SLURM_ARRAY_JOB_ID:?}-$id"
python3 "$src/coupon.py" 7
work="case-$SLURM_ARRAY_JOB_ID-7"
python3 "$src/escape.py" "$work" "$seed"
python3 "$src/validate_escape.py" "$work/escape-$seed.json"
python3 "$src/reservations.py" "$work/inputs.json" --local
