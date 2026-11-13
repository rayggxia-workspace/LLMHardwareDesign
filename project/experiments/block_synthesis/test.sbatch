#!/bin/bash
#SBATCH --job-name=yzl-syn-test
#SBATCH --partition=c64
#SBATCH --cpus-per-task=4
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/*) ;; *) exit 2;; esac
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$2/deps${PYTHONPATH:+:$PYTHONPATH}"
cd "$root"
sha256sum *.py > input.sha256
"$python" -m unittest discover -v -p 'test_*.py' > tests.log 2>&1
"$python" -B static_conflict_probe.py > static-conflict.json
sha256sum tests.log static-conflict.json > output.sha256
