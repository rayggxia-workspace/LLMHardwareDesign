#!/bin/bash
#SBATCH --job-name=yzl-topo-bound
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
mkdir generated
"$python" -u -B topology_diagnostics.py "$2" "$3" generated/topologies.json --wire-budget "$4" > diagnostic.log 2>&1
sha256sum generated/* tests.log diagnostic.log > output.sha256
