#!/bin/bash
set -euo pipefail
g=$1
d=$2
codecs=/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/staged/project
export PYTHONPATH="$PWD/algo1:$codecs/control_image_v0_1:$codecs/control_isa_v0_1"
pos=$SLURM_ARRAY_TASK_ID
(cd "$g/packed-rows" && sha256sum -c "row-$pos.tar.sha256")
python3.11 -B audit_full_native.py "$g/packed-rows/row-$pos.tar" "$d/request-110369/local-sidecars.json" \
 algo1/blockv2-mod.json "evidence/full-native-$SLURM_ARRAY_JOB_ID-$pos"
