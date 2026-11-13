#!/bin/bash
#SBATCH --job-name=yzl-syn-embed
#SBATCH --partition=c64
#SBATCH --cpus-per-task=4
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/algorithm-fix-*) ;; *) exit 2;; esac
cd "$root"
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK OPENBLAS_NUM_THREADS=$SLURM_CPUS_PER_TASK
export PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/cp-environment-v2/deps:/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/deps
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
sha256sum *.py *.sbatch "$2" "$3" "$4/"*.safetensors > input.sha256
"$python" -m unittest discover -v -p 'test_*.py' > tests.log 2>&1
"$python" -u embedding_validation.py "$2" "$3" "$4" generated > embedding.log 2>&1
sha256sum tests.log generated/model.json generated/result.json generated/summary.json generated/embedding-int16.npy > output.sha256
