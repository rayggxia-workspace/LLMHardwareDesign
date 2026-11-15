#!/bin/bash
set -euo pipefail
native=/public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project/experiments/block_local_native
codecs=/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/staged/project
export PYTHONPATH="$PWD/compiler:$PWD/algo1:$native:$codecs/control_image_v0_1:$codecs/control_isa_v0_1"
python3.11 -B compiler/test_native_backend_graph.py evidence/recipe-graph-113998/recipe-graph.json "evidence/native-backend-$SLURM_JOB_ID"
