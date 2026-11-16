#!/bin/bash
#SBATCH --job-name=yzl-syn-mem
#SBATCH --partition=c64
#SBATCH --cpus-per-task=4
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
envroot=$(realpath "$2")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/algorithm-fix-*) ;; *) exit 2;; esac
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$envroot/deps:/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/deps${PYTHONPATH:+:$PYTHONPATH}"
cd "$root"
sha256sum *.py "$4" > input.sha256
"$python" -B evaluate_memory.py "$3" "$4" "$5" "$root/result" > evaluation.log 2>&1
find result -name '*.json' -print0 | sort -z | xargs -0 sha256sum > output.sha256
