#!/bin/bash
#SBATCH --job-name=yzl-phase-seed
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
sha256sum *.py *.cpp *.sbatch "$2" "$3" > input.sha256
"$python" -B -m unittest discover -p 'test_*.py' -q > tests.log 2>&1
mkdir diagnostic
"$python" -u -B diagnose_tile_barriers.py "$2" "$3" diagnostic/barriers.json > barriers.log 2>&1
"$python" -u -B selected_order_profile.py "$2" "$3" diagnostic/critical-chain.json > chain.log 2>&1
"$python" -u -B search_diagnostics.py "$2" "$3" diagnostic/bounds.json > bounds.log 2>&1
sha256sum diagnostic/* > diagnostic-output.sha256
# The input already contains the common phase pool. Do not register it twice
# or silently introduce windows, channels, SRAM or a new action family.
"$python" -u -B tile_review.py "$2" generated --registered-ir --incumbent "$3" \
  --incumbent-backbone --wire-budget "$4" --width 8 \
  --policies old-dp conditional-dp resource-dp > review.log 2>&1
sha256sum generated/* diagnostic/* tests.log review.log barriers.log chain.log bounds.log > output.sha256
