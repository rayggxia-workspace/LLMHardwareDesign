#!/bin/bash
#SBATCH --job-name=lrz-i61-receive
#SBATCH --partition=c96
#SBATCH --cpus-per-task=2
#SBATCH --time=00:20:00
set -euo pipefail
root=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023
model=$1
case "$model" in
 gemma) capture=gemma-capture01 ;;
 qwen25|qwen35) capture=$model-gqa01 ;;
 phi) capture=phi-reserved01 ;;
 *) exit 2 ;;
esac
export TMPDIR="$root/tmp" PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
python="$root/venv-modern/bin/python"
if [ "$model" != phi ] && [ ! -e "$root/$model-independent01.json" ]; then
 "$python" -u -B "$root/phase13/receive_probe.py" --result "$root/$model-integer01" --capture "$root/$capture" --out "$root/$model-independent01.json"
fi
"$python" -u -B "$root/phase13/export_capture.py" --capture "$root/$capture" --binding "$root/phase13/binding.json" --out "$root/$model-strict02"
"$python" -u -B "$root/phase13/validate_export.py" --capture "$root/$capture" --export "$root/$model-strict02" --out "$root/$model-export-source02.json"
