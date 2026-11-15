#!/bin/bash
set -euo pipefail
export PYTHONPATH="$PWD/algo1:/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/staged/project/control_image_v0_1"
out="evidence/instructions-$SLURM_JOB_ID"
python3.11 -B package_full_native.py "$1" "$2" "$3" "$out"
python3.11 -B validate_instruction_package.py "$out"
