#!/bin/bash
#SBATCH --job-name=yzl-sc153-export25
#SBATCH --partition=c96
#SBATCH --cpus-per-task=8
#SBATCH --time=01:00:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK MKL_NUM_THREADS=$SLURM_CPUS_PER_TASK
/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python "$ROOT/src/export_checkpoint.py" --model /public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/models/qwen25-3b-5defd279 --out "$ROOT/qwen25-r1" --prompt Hello --new-tokens 3
