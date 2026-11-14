#!/usr/bin/env bash
set -euo pipefail
cd "$1"
g="$2"; base="$3"
r=/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/staged/project
export PYTHONPATH="$PWD:$g:$r/control_image_v0_1:$r/control_isa_v0_1"
/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python -B audit-gather-contract.py "$g/../r4/rows/row-0/embedding" "$base" "contract-$SLURM_JOB_ID"
sha256sum resident_gather_contract.py "contract-$SLURM_JOB_ID/"{local.pm,demand.json,unbound.json,summary.json}
