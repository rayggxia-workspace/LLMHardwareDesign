#!/bin/bash
set -eu
f=$1
page=$2
base=$3
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$f"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
"$py" -B check_algo1.py "$page" "$base" "evidence/algo1-$SLURM_JOB_ID.json"
