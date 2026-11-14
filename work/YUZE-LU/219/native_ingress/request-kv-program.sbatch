#!/usr/bin/env bash
set -euo pipefail
cd "$1"
g=$2
handoff=$3
project=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/framework-20261114-akeox2em
router="$project/router-current/project/experiments/upper_router"
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$g:$router"
"$py" -B audit_request_kv_program.py "$g/../request-runtime-r2" \
  /public/home/yuzelu/project-circuit/issue260-request-kv-binding-dbIUacE6/bound-104206 "$handoff" "kv-$SLURM_JOB_ID.json"
sha256sum "kv-$SLURM_JOB_ID.json"
