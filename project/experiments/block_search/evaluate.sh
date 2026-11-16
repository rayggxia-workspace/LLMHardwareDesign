#!/bin/bash
#SBATCH --job-name=yzl-bs-eval
#SBATCH --partition=c64
#SBATCH --cpus-per-task=2
set -euo pipefail
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2 PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/deps
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
cd "$1"
"$python" -B -m unittest -v test_search
"$python" -B -u evaluate.py /public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026 "$2" --full "$3"
