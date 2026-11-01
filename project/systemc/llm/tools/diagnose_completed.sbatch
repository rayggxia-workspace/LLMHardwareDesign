#!/bin/bash
#SBATCH --job-name=yzl-sc153-conditional
#SBATCH --partition=c64
#SBATCH --nodelist=node1
#SBATCH --cpus-per-task=4
#SBATCH --time=00:30:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
REV=${1:?revision required}
export ROOT REV
printf '%s\n' phi qwen25 qwen3 gemma | xargs -n1 -P4 bash -c '
 set -euo pipefail
 export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 SLURM_CPUS_PER_TASK=1 PYTHONDONTWRITEBYTECODE=1
 export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
 MODEL=$0;CP="$MODEL-r8"
 case "$MODEL" in phi|qwen25) LAYER=30;; qwen3) LAYER=27;; gemma) LAYER=33;; esac
 case "$MODEL" in qwen25|qwen3) CP="$MODEL-r2";; esac
 /public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python "$ROOT/src-$REV/project/systemc/llm/tools/diagnose_dense_layer.py" "$ROOT/$CP" "$ROOT/run-$MODEL-$REV" "$LAYER" > "$ROOT/logs/conditional-$MODEL-$REV.log" 2>&1
'
