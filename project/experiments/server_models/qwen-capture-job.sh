#!/bin/bash
#SBATCH --job-name=lrz-i61-qgqa
#SBATCH --partition=c96
#SBATCH --cpus-per-task=24
#SBATCH --time=02:00:00
set -euo pipefail
root=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023
model=$1
case "$model" in
 qwen25) modeldir=qwen25-3b-5defd279 ;;
 qwen35) modeldir=qwen35-4b-851bf6e8 ;;
 *) exit 2 ;;
esac
export TMPDIR="$root/tmp" HF_HOME="$root/cache" TORCH_HOME="$root/cache"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_IMPLICIT_TOKEN=1 TOKENIZERS_PARALLELISM=false
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=24 MKL_NUM_THREADS=24 OPENBLAS_NUM_THREADS=1
"$root/venv-modern/bin/python" -u -B "$root/phase7/capture.py" --model "$model" --model-dir "$root/models/$modeldir" --plan "$root/phase6/qwen-mirror-plan.json" --binding "$root/phase7/binding.json" --threads 24 --out "$root/$model-gqa01"
