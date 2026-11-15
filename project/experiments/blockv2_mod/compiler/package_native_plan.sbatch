#!/bin/bash
set -euo pipefail
n=/public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project/experiments
codecs=/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/staged/project
export PYTHONPATH="$PWD/compiler:$PWD/algo1:$n/block_local_native:$n/mother_control_native:$codecs/control_image_v0_1:$codecs/control_isa_v0_1"
python3.11 -B compiler/package_native_plan.py "$1" "evidence/native-package-$SLURM_JOB_ID"
