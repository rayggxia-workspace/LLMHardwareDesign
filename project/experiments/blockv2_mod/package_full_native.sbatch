#!/bin/bash
set -euo pipefail
export PYTHONPATH="$PWD/algo1"
python3.11 -B package_full_native.py "$1" "$2" "$3" "evidence/instructions-$SLURM_JOB_ID"
