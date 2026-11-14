#!/usr/bin/env bash
set -euo pipefail
cd "$1"
g="$2"; d="$3"
root=/public/home/yuzelu/project-circuit
a="$root/issue250-u-n32-stored-link-20261112-01/staged/project"
mc="$root/issue234-native-fixed-skip-request-H2gY5uiN/source/project/experiments/mother_control_native"
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$PWD:$d:$g:$a/control_isa_v0_1:$mc"
"$py" -B link_gather_request.py "$g/../request-runtime-r2" "$d/request-110369" \
  "$g/native-dispatch-109637/report.json" "link-$SLURM_JOB_ID"
sha256sum "link-$SLURM_JOB_ID/"{mother.pm,request-link.json} link_gather_request.py
