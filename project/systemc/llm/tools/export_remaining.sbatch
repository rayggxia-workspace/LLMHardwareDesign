#!/bin/bash
#SBATCH --job-name=yzl-sc153-export8
#SBATCH --partition=c64
#SBATCH --cpus-per-task=16
#SBATCH --time=02:00:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=4 MKL_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 SC_EXPORT_THREADS=4
PY=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export ROOT PY
free -b
awk '/MemAvailable/ {if ($2 < 120*1024*1024) exit 1}' /proc/meminfo
printf '%s\n' \
 'phi /public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/models/phi4mini-cfbefacb' \
 'gemma /public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/models/gemma3-4b-093f9f38' \
 'qwen35 /public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/models/qwen35-4b-851bf6e8' \
 'falcon /public/home/yuzelu/RuizhiLiang/issue70-moe-hybrid-20261024/models-relay/falcon' |
 xargs -n2 -P4 bash -c '"$PY" "$ROOT/continuation-r8/export_remaining.py" --model "$1" --out "$ROOT/$0-r8" --new-tokens 3 > "$ROOT/logs/export-$0-r8.log" 2>&1'
