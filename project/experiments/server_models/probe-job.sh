#!/bin/bash
#SBATCH --job-name=lrz-i61-backend
#SBATCH --partition=c96
#SBATCH --cpus-per-task=4
#SBATCH --time=00:10:00
set -euo pipefail
root=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023
export TMPDIR="$root/tmp" HF_HOME="$root/cache" TORCH_HOME="$root/cache"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_HUB_DISABLE_IMPLICIT_TOKEN=1
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
/public/home/yuzelu/RuizhiLiang/issue53-cpu-pilot-20261023/venv/bin/python -B "$root/phase4/probe_backend.py" \
 --root "$root/models" --out "$root/backend01.json"
