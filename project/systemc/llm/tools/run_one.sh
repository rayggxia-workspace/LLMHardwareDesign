#!/bin/bash
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
CHECKPOINT=$1; RUN=$2; MODE=$3; REV=${4:-r6}
export SLURM_CPUS_PER_TASK=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
if [ "$MODE" = fused ]; then export LLM_NORM_FUSED=1; else unset LLM_NORM_FUSED; fi
cd "$ROOT"
mkdir -p "$RUN"
exec >"logs/round6-$RUN.out" 2>"logs/round6-$RUN.err"
sha256sum "systemc-src-$REV.tar.gz" "build-$REV/llm_bench" >"$RUN/run-inputs.sha256"
"build-$REV/llm_bench" "$ROOT/$CHECKPOINT" "$ROOT/$RUN"
/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python "src-$REV/project/systemc/llm/tools/validate_inference.py" "$ROOT/$CHECKPOINT" "$ROOT/$RUN"
