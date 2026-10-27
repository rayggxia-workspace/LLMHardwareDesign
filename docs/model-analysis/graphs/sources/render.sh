#!/bin/bash
#SBATCH --job-name=yzl-opgraph-render
#SBATCH --partition=c96
#SBATCH --cpus-per-task=4
#SBATCH --mem=0
#SBATCH --time=0
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026
PY=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK MKL_NUM_THREADS=$SLURM_CPUS_PER_TASK
export PYTHONPATH="$ROOT/deps${PYTHONPATH:+:$PYTHONPATH}"
export TMPDIR="$ROOT/tmp" HF_HOME="$ROOT/cache"
"$PY" "$ROOT/sources/manual_graphs.py" --out "$ROOT/results/manual02"
"$PY" "$ROOT/sources/render_exports.py"
cd "$ROOT"
tar --exclude='*.onnx' -czf inspection01.tgz results/native02 results/native03 results/native04 results/manual02 results/render01 sources
