#!/bin/bash
set -euo pipefail
framework=$1
graph=$2
hardware=$3
root="$PWD"
project=$(dirname "$root")
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
native=/public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project/experiments/block_local_native
codecs=/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/staged/project
export PYTHONPATH="$root/compiler:$root/algo1:$framework:$native:$native/../mother_control_native:$codecs/control_image_v0_1:$codecs/control_isa_v0_1:$project/chip-state-replay-20261113/deps:$project/../operator-graphs-20261026/deps"
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
"$py" -B compile_graph_input.py "$graph" "$hardware" --output "evidence/two-input-$SLURM_JOB_ID"
