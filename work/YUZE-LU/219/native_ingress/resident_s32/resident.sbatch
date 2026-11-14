#!/usr/bin/env bash
set -euo pipefail
cd "$1"
g=$2
readback=$3
router=$4
handoff=$5
isa=$6
export PYTHONPATH="$g:$readback:$router"
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
"$py" -B prepare_resident_s32_add.py "$g/../r4/rows/row-0/layer-00/residual" \
  "$handoff/base.json" "$g/../v2-candidate-embedding/control-fabric" "$handoff" \
  "$isa" c-e32-profile.json "resident-$SLURM_JOB_ID"
sha256sum "resident-$SLURM_JOB_ID"/{residual-proof,algorithm2-input}.json
