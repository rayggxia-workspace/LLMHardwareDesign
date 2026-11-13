#!/bin/bash
#SBATCH --job-name=yzl-syn-audit
#SBATCH --partition=c64
#SBATCH --cpus-per-task=4
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/*) ;; *) exit 2;; esac
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$2/deps:/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/deps"
cd "$root"
sha256sum *.py > source.sha256
"$python" run.py "$3" "$4" "$root/coverage" --audit-only > audit.log 2>&1
sha256sum coverage/* > results.sha256
