#!/usr/bin/env bash
set -euo pipefail
cd "$1"
g="$2"; dma="$3"; stage="$4"; ports="$5"
r=/public/home/yuzelu/project-circuit/issue250-u-n32-stored-link-20261112-01/staged/project
router=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/framework-20261114-akeox2em/router-current/project/experiments/upper_router
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$PWD:$g:$r/control_image_v0_1:$r/control_isa_v0_1:$router"
sha256sum -c "$stage/artifacts.sha256"
"$py" -B publish-resident-gather.py "$dma/base-110165.json" "$stage" "$ports" \
 "$g/../r4/rows/row-0/embedding/compile.json" "$6" \
 "$g/draft-native-dma-handoff-109815/algorithm2-input.json" "handoff-$SLURM_JOB_ID" --prompt-address 4590743552
sha256sum "handoff-$SLURM_JOB_ID/"{summary.json,algorithm2-input.json,local.pm}

