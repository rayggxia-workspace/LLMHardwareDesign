#!/bin/bash
#SBATCH --job-name=yzl-future-tail
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/algorithm-fix-*) ;; *) exit 2;; esac
cd "$root"
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK OPENBLAS_NUM_THREADS=$SLURM_CPUS_PER_TASK
export PYTHONPATH=$root:/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/cp-environment-v2/deps:/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/deps
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
sha256sum *.py *.cpp *.sbatch "$2" "$3" "$5" > input.sha256
"$python" -B -m unittest discover -p 'test_*.py' -q > tests.log 2>&1
# Inputs contain the already qualified common pool. Preserve it byte-for-byte;
# the only new decision is frontier ranking. The strongest checked previous
# conditional-DP plan is retained as both incumbent and same-pool denominator.
"$python" -u -B tile_review.py "$2" generated --registered-ir --incumbent "$3" \
  --same-pool-baseline "$5" --incumbent-backbone --wire-budget "$4" --width 8 \
  --policies future-greedy future-dp > review.log 2>&1
sha256sum generated/* tests.log review.log > output.sha256
