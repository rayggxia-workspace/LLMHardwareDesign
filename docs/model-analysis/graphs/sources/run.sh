#!/bin/bash
#SBATCH --job-name=yzl-opgraph
#SBATCH --partition=c96
#SBATCH --cpus-per-task=8
#SBATCH --mem=0
#SBATCH --time=0
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026
PY=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK MKL_NUM_THREADS=$SLURM_CPUS_PER_TASK
export PYTHONPATH="$ROOT/deps${PYTHONPATH:+:$PYTHONPATH}"
export TMPDIR="$ROOT/tmp" HF_HOME="$ROOT/cache"
mkdir -p "$ROOT/tmp" "$ROOT/cache"
"$PY" -m pip install --no-index --no-deps --target "$ROOT/deps" "$ROOT"/wheels/*.whl
"$PY" "$ROOT/sources/native_export.py" --root "$ROOT/results/pilot01" --model qwen3
