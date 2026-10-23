#!/bin/bash
#SBATCH --job-name=lrz-i61-integer
#SBATCH --partition=c96
#SBATCH --cpus-per-task=2
#SBATCH --time=00:45:00
set -euo pipefail
root=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023
case "$1" in
 gemma) capture=gemma-capture01 ;;
 qwen25|qwen35) capture=$1-gqa01 ;;
 *) exit 2 ;;
esac
export TMPDIR="$root/tmp" PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
/public/home/yuzelu/RuizhiLiang/issue53-cpu-pilot-20261023/venv/bin/python -u -B "$root/phase8/quant_probe.py" --capture "$root/$capture" --binding "$root/phase8/binding.json" --out "$root/$1-integer01"
