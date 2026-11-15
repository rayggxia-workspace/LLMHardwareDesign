#!/bin/bash
set -euo pipefail
root=$(pwd)
framework=$1
event_ir=$2
hardware=$3
output=$4
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$root/algo1:$framework"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
"$py" -B "$root/algo1_blockv2_mod.py" --legacy-symbolic-diagnostic "$event_ir" "$hardware" "$output"
