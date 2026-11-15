#!/bin/bash
set -euo pipefail
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
PYTHONPATH="$PWD/compiler" "$py" -B compiler/test_value_layout.py evidence/recipe-graph-113998/recipe-graph.json "evidence/value-layout-$SLURM_JOB_ID"
