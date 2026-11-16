#!/bin/bash
#SBATCH --job-name=yzl-tile-recompile
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/algorithm-fix-*) ;; *) exit 2;; esac
cd "$root"
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK OPENBLAS_NUM_THREADS=$SLURM_CPUS_PER_TASK
export PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/cp-environment-v2/deps:/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/deps
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
sha256sum *.py "$2" > input.sha256
"$python" -B -m unittest discover -p 'test_*.py' -q > tests.log 2>&1
"$python" -u -B recompile_ir.py "$2" corrected > recompile.log 2>&1
"$python" -u -B tile_review.py corrected/ir.json generated --registered-ir --wire-budget "$3" \
 --policies greedy old-dp conditional-greedy conditional-dp > review.log 2>&1
sha256sum corrected/* generated/* tests.log recompile.log review.log > output.sha256
