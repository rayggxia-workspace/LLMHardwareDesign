#!/bin/bash
#SBATCH --job-name=yzl-column-plan
#SBATCH --partition=c64
#SBATCH --cpus-per-task=4
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/*) ;; *) exit 2;; esac
cd "$root"
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/cp-environment-v2/deps
sha256sum *.py "$2"/*-ir.json "$3"/*-budget-*.json > input.sha256
"$python" -B -m unittest discover -p 'test_*.py' -v > tests.log 2>&1
"$python" -u -B column_review.py "$2" "$3" generated --scenario "$4" > plan.log 2>&1
sha256sum generated/* tests.log > output.sha256
