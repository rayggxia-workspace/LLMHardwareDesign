#!/bin/bash
#SBATCH --job-name=yzl-reuse-compare
#SBATCH --partition=c64
#SBATCH --cpus-per-task=4
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/*) ;; *) exit 2;; esac
cd "$root"
sha256sum *.py "$2"/*json "$3"/*json > input.sha256
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
"$python" reuse_compare.py "$2" "$3" > equivalence.json
sha256sum equivalence.json > output.sha256
