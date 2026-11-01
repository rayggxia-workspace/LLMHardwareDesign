#!/bin/bash
#SBATCH --job-name=yzl-sc153-silu-layer
#SBATCH --partition=c64
#SBATCH --nodelist=node1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:30:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
cd "$ROOT"
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LLM_PRECISE_ADAPTER=1 LLM_BLOCK_SCALES=1 LLM_ACCURATE_SILU=1 LLM_TRACE_LAYER=1
RUN=firstbad-qwen25-r35-r37
mkdir "$RUN"
sha256sum systemc-src-r35.tar.gz build-r35/llm_bench src-r35/project/systemc/llm/tools/diagnose_dense_layer.py continuation-r8/silu-layer-r37.sbatch > "$RUN/run-inputs.sha256"
build-r35/llm_bench "$ROOT/qwen25-r2" "$ROOT/$RUN" 1 > "logs/$RUN.log" 2>&1
/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python src-r35/project/systemc/llm/tools/diagnose_dense_layer.py "$ROOT/qwen25-r2" "$ROOT/$RUN" 1 >> "logs/$RUN.log" 2>&1
