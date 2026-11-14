#!/usr/bin/env bash
set -euo pipefail
cd "$1"
g="$2";d="$3"; link="$4"
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
router=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/framework-20261114-akeox2em/router-current/project/experiments/upper_router
export PYTHONPATH="$g:$router"
"$py" -B inventory_vocab_aux.py "$d/geometry-110384/base.json" "$g/../audit-v2-data-link-r2.py" "$link" "aux-$SLURM_JOB_ID.json"
sha256sum "aux-$SLURM_JOB_ID.json"
