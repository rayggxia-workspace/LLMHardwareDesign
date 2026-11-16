#!/bin/bash
#SBATCH --job-name=yzl-reuse-audit
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
"$python" -m unittest discover -v -p 'test_*.py' > tests.log 2>&1
"$python" static_conflict_probe.py > static-conflict.json
"$python" reuse_audit.py "$2" > whole-plan-audit.json
sha256sum tests.log static-conflict.json whole-plan-audit.json > output.sha256
