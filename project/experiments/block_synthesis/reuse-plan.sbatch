#!/bin/bash
#SBATCH --job-name=yzl-reuse-plan
#SBATCH --partition=c64
#SBATCH --cpus-per-task=4
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/*) ;; *) exit 2;; esac
cd "$root"
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/deps:/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/cp-environment-v2/deps
sha256sum *.py "$2" "$3" "$4" "$5"/native-*.log "$6" > input.sha256
"$python" full_plan.py --read-cache --primitive-program "$6" "$2" "$3" "$4" "$5" generated > plan.log 2>&1
sha256sum generated/* > output.sha256
