#!/bin/bash
set -euo pipefail
framework=$1
root=$PWD
project=$(dirname "$root")
native=/public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project/experiments/block_local_native
export PYTHONPATH="$root/compiler:$framework:$native:$project/chip-state-replay-20261113/deps:$project/../operator-graphs-20261026/deps"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python -B compiler/build_recipe_graph.py "$project/full-qwen25-3b-v1/complete/full.onnx" "evidence/recipe-graph-$SLURM_JOB_ID"
