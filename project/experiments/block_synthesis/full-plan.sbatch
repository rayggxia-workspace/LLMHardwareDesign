#!/bin/bash
#SBATCH --job-name=yzl-full-plan
#SBATCH --partition=c64
#SBATCH --cpus-per-task=4
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/*) ;; *) exit 2;; esac
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/deps:/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/cp-environment-v2/deps
cd "$root"
sha256sum *.py > input.sha256
options=()
if [[ -n "${6:-}" ]]; then options+=(--primitive-program "$6");fi
"$python" full_plan.py "${options[@]}" "$2" "$3" "$4" "$5" generated
sha256sum generated/* > output.sha256
