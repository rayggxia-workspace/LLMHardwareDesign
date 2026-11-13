#!/bin/bash
#SBATCH --job-name=yzl-resident-scatter
#SBATCH --partition=c64,c96
#SBATCH --cpus-per-task=4
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/*) ;; *) exit 2;; esac
cd "$root"
ulimit -c 0
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK OPENBLAS_NUM_THREADS=$SLURM_CPUS_PER_TASK
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/cp-environment-v2/deps:/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/deps
PY=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
sha256sum source.tar resident-scatter.sbatch "$2" "$3" > input.sha256
"$PY" -m unittest discover -s . -p 'test_*.py' > tests.log 2>&1
"$PY" resident_scatter_survey.py "$2" "$3" generated --width 8 > survey.log 2>&1
sha256sum generated/summary.json generated/programs.json > output.sha256
