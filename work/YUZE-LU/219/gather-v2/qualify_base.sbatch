#!/usr/bin/env bash
set -euo pipefail
cd "$1"
work="$2"
g="$3"
detail="$PWD/detail-$4"
pins="$PWD/client3-$5.tsv"
export PYTHONPATH="$g"
python3 -B extend_gather_route_base.py "$work/routed-handoff-109893/base.json" \
 "$detail" "$pins" "base-$SLURM_JOB_ID.json"
sha256sum "base-$SLURM_JOB_ID.json" extend_gather_route_base.py > "base-$SLURM_JOB_ID.sha256"
