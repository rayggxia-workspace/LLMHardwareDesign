#!/bin/bash
set -euo pipefail
native=/public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project/experiments/block_local_native
export PYTHONPATH="$PWD/tlm:$PWD/compiler:$native:/public/home/yuzelu/project-circuit/issue260-tlm-request-Xuwu5O"
python3.11 -B tlm/verify_streamed_projection.py "$1" "evidence/streamed-projection-$SLURM_JOB_ID.json"
