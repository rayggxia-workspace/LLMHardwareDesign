#!/bin/bash
#SBATCH --job-name=yzl-phase-audit
#SBATCH --partition=c64
#SBATCH --cpus-per-task=4
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/*) ;; *) exit 2;; esac
cd "$root"
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
sha256sum *.py "$2" "$3" > input.sha256
"$python" -u -B phase_accounting.py "$2" "$3" phase-accounting.json > phase.log 2>&1
sha256sum phase-accounting.json phase.log > output.sha256
