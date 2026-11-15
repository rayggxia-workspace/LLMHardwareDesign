#!/bin/bash
set -euo pipefail
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export PYTHONPATH="$1"
python3.11 -B compile_full_native.py "$2" "evidence/replan-$SLURM_JOB_ID"
