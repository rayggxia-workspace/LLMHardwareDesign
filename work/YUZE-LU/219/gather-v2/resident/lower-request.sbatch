#!/usr/bin/env bash
set -euo pipefail
cd "$1"
g="$2"; index="$3"
r=/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/staged/project
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$PWD:$index:$g:$r/control_image_v0_1:$r/control_isa_v0_1"
"$py" -B lower_request_gather.py "$index/check-native-ingress.py" "$g/../packed-rows" \
 "$index/receipt-110128/input-index.tsv" "request-$SLURM_JOB_ID" --workers "$SLURM_CPUS_PER_TASK"
sha256sum "request-$SLURM_JOB_ID/"{summary.json,local-sidecars.json} lower_request_gather.py
