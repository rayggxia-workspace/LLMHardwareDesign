#!/bin/bash
#SBATCH --job-name=yzl-search-bound
#SBATCH --partition=c64
#SBATCH --cpus-per-task=4
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/*) ;; *) exit 2;; esac
cd "$root"
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/cp-environment-v2/deps
sha256sum *.py "$2"/*json > input.sha256
"$python" -B -m unittest discover -p 'test_*.py' -v > tests.log 2>&1
for name in five-groups nine-groups-count-experiment; do
    "$python" -B search_diagnostics.py "$2/$name-ir.json" "$2/$name-plan.json" "$name-bound.json"
done
sha256sum *-bound.json tests.log > output.sha256
