#!/usr/bin/env bash
set -euo pipefail
cd "$1"
g=$2
d=$3
feedback=$4
project=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/framework-20261114-akeox2em
router="$project/router-current/project/experiments/upper_router"
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$g:$router"
"$py" -B publish_native_request_handoff.py "$g/../request-runtime-r2" "$d/geometry-110384/base.json" \
  "$g/../v2-native-control-request-r2/requirements.json" "$g/ingress-route-iN0LbH/routed-handoff-109893/compile.json" \
  "$d/geometry-110384" "$d/mother-ingress-sNMsK9/link-110415" "$feedback" "$d/request-110369" \
  "$g/../v2-candidate-embedding/control-fabric" "$d/handoff-110385/algorithm2-input.json" \
  block-v2-request-rewrites.json "handoff-$SLURM_JOB_ID"
if [[ ${5:-route} != route ]]; then exit 0; fi
"$py" -B "$router/run.py" "handoff-$SLURM_JOB_ID/algorithm2-input.json" "route-$SLURM_JOB_ID.json" \
  --handoff "handoff-$SLURM_JOB_ID" --access-pitch 400 --rounds 1 --max-expansions 2000
