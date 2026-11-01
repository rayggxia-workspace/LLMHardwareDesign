#!/bin/bash
#SBATCH --job-name=yzl-sc153-phifuse
#SBATCH --partition=c64
#SBATCH --nodelist=node1
#SBATCH --cpus-per-task=1
#SBATCH --time=00:30:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
cd "$ROOT"
export LLM_NORM_FUSED=1 LLM_TRACE_LAYER=30 PYTHONDONTWRITEBYTECODE=1
export SLURM_CPUS_PER_TASK=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
RUN=run-phi-fused-r13
mkdir "$RUN"
sha256sum systemc-src-r13.tar.gz build-r13/llm_bench phi-r8/metadata.txt phi-r8/weights.index > "$RUN/run-inputs.sha256"
build-r13/llm_bench "$ROOT/phi-r8" "$ROOT/$RUN"
/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python src-r13/project/systemc/llm/tools/validate_inference.py "$ROOT/phi-r8" "$ROOT/$RUN"
