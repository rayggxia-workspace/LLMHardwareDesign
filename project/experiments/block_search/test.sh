#!/bin/bash
#SBATCH --job-name=yzl-bs-test
#SBATCH --partition=c64
#SBATCH --cpus-per-task=1
set -euo pipefail
export PYTHONDONTWRITEBYTECODE=1
cd "$1"
python=${2:-/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python}
"$python" -B -m unittest -v test_search
sha256sum search.py evaluate.py test_search.py
