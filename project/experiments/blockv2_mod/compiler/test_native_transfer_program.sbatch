#!/bin/bash
set -euo pipefail
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
native=/public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project/experiments/block_local_native
codecs=/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/staged/project
export PYTHONPATH="$PWD/compiler:$PWD/algo1:$native:$codecs/control_image_v0_1:$codecs/control_isa_v0_1"
"$py" -B compiler/test_native_transfer_program.py evidence/recipe-graph-113998/recipe-graph.json evidence/operand-recipes-114085/operand-recipes.json "evidence/native-transfers-$SLURM_JOB_ID"
