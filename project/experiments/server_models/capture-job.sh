#!/bin/bash
#SBATCH --job-name=lrz-i61-capture
#SBATCH --partition=c96
#SBATCH --cpus-per-task=24
#SBATCH --time=03:00:00
set -euo pipefail
root=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023
model=$1
case "$model" in
 gemma) modeldir=gemma3-4b-093f9f38; out=gemma-capture01 ;;
 phi) modeldir=phi4mini-cfbefacb; out=phi-reserved01 ;;
 *) exit 2 ;;
esac
export TMPDIR="$root/tmp" HF_HOME="$root/cache" TORCH_HOME="$root/cache"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_IMPLICIT_TOKEN=1 TOKENIZERS_PARALLELISM=false
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=24 MKL_NUM_THREADS=24 OPENBLAS_NUM_THREADS=1
test "${SLURM_CPUS_PER_TASK}" -eq 24
/public/home/yuzelu/RuizhiLiang/issue53-cpu-pilot-20261023/venv/bin/python -u -B "$root/phase5/capture.py" \
 --model "$model" --model-dir "$root/models/$modeldir" --plan "$root/phase3/mirror-plan.json" \
 --binding "$root/phase5/binding.json" --threads 24 --out "$root/$out"
