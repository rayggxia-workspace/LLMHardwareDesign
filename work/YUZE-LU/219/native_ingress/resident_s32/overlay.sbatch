#!/usr/bin/env bash
set -euo pipefail
cd "$1"
g=$2
readback=$3
router=$4
handoff=$5
export PYTHONPATH="$g:$readback:$router"
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
"$py" -B publish_residual_route_overlay.py "$handoff" resident-111950 egress-111983/egress.json "overlay-$SLURM_JOB_ID"
sha256sum "overlay-$SLURM_JOB_ID"/{handoff,algorithm2-input}.json
