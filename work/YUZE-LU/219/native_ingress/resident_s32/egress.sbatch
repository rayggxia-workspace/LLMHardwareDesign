#!/usr/bin/env bash
set -euo pipefail
cd "$1"
g=$2
joint=$3
readback=$4
router=$5
stored=$6
isa=$7
gather_image=$8
gather_sha=$9
export PYTHONPATH="$stored:$g/ingress-route-iN0LbH:$g:$readback:$router"
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
"$py" -B export_residual_egress.py resident-111950 "$g/../r4/rows/row-0/layer-00/next-rms" \
  "$joint/handoff-111294" "$gather_image" "$isa" "egress-$SLURM_JOB_ID" --gather-sha256 "$gather_sha"
sha256sum "egress-$SLURM_JOB_ID/egress.json"
