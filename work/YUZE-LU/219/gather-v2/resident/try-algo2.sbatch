#!/usr/bin/env bash
set -euo pipefail
cd "$1"
base="$2"; r="$3"
py=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
"$py" -B "$r/run.py" "$base/algorithm2-input.json" "algo2-$SLURM_JOB_ID.json" \
 --handoff "$base" --access-pitch 400 --rounds 1 --max-expansions 2000
sha256sum "algo2-$SLURM_JOB_ID.json"
