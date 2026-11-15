#!/bin/bash
set -euo pipefail
native=/public/home/yuzelu/project-circuit/issue260-product-retirement-V6JR7Km4/source/project/experiments
export PYTHONPATH="$PWD/tlm:$PWD/compiler:$native/block_local_native:$native/native_s32_n:/public/home/yuzelu/project-circuit/issue260-tlm-request-Xuwu5O"
python3.11 -B tlm/verify_package_providers.py "$1" hardware/blockv2-mod-nine.json "$native/w8a16_g/reference.py" "evidence/package-providers-$SLURM_JOB_ID.json"
