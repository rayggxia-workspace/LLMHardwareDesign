#!/bin/bash
#SBATCH --job-name=yzl-bs-export
#SBATCH --partition=c64
#SBATCH --cpus-per-task=2
set -euo pipefail
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/deps
exec /public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python -u "$1/export_full.py" "$2" "$3"
