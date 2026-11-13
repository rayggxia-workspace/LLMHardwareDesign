#!/bin/bash
#SBATCH --job-name=yzl-bs-audit
#SBATCH --partition=c64
#SBATCH --cpus-per-task=1
set -euo pipefail
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/deps
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
"$python" "$1/report.py" "$2" "$2/report.html"
"$python" "$1/collect.py" "$2" "$3" --jobs "$4" --source-commit "$5"
