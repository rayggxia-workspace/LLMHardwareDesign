#!/bin/bash
#SBATCH --job-name=yzl-plan-report
#SBATCH --partition=c64
#SBATCH --cpus-per-task=2
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/*) ;; *) exit 2;; esac
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
cd "$root"
mkdir generated
cp "$2"/{summary.json,nine-groups-count-experiment-ir.json,nine-groups-count-experiment-plan.json,nine-groups-count-experiment-baseline.json} generated/
sha256sum *.py generated/*.json > input.sha256
"$python" full_report.py generated
sha256sum generated/report.html > output.sha256
