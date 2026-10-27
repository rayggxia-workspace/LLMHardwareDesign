#!/bin/bash
#SBATCH --job-name=yzl-opgraph-native
#SBATCH --partition=c96
#SBATCH --cpus-per-task=8
#SBATCH --mem=0
#SBATCH --time=0
#SBATCH --array=0-9%3
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026
PY=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK MKL_NUM_THREADS=$SLURM_CPUS_PER_TASK
export PYTHONPATH="$ROOT/deps${PYTHONPATH:+:$PYTHONPATH}"
export TMPDIR="$ROOT/tmp" HF_HOME="$ROOT/cache"
MODELS=(qwen3 qwen25 llama gemma_local gemma_global phi qwen35_global qwen35_linear granite falcon)
"$PY" "$ROOT/sources/native_export.py" --root "$ROOT/results/native02" --model "${MODELS[$SLURM_ARRAY_TASK_ID]}"
