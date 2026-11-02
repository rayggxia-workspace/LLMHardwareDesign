#!/bin/bash
#SBATCH --job-name=yzl-sc153-audit
#SBATCH --partition=c64
#SBATCH --cpus-per-task=2
#SBATCH --time=00:10:00
set -euo pipefail
export ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python "$ROOT/src/audit_bench.py"
