#!/bin/bash
#SBATCH --job-name=yzl-sc153-firstbad
#SBATCH --partition=c64
#SBATCH --nodelist=node1
#SBATCH --cpus-per-task=3
#SBATCH --time=00:30:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
cd "$ROOT"
export ROOT
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 SLURM_CPUS_PER_TASK=1 PYTHONDONTWRITEBYTECODE=1
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONPATH="$ROOT/src-r33/project/systemc/llm/tools"
PY=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PY
printf '%s\n' r31 r33 oracle | xargs -n1 -P3 bash -c '
 set -euo pipefail
 export LLM_PRECISE_ADAPTER=1 LLM_TRACE_LAYER=1
 if [ "$0" = oracle ];then
  RUN=oracle-qwen25-hidden-r34;mkdir "$RUN"
  ln -s "$ROOT/run-qwen25-r31/systemc_receipt.json" "$RUN/systemc_receipt.json"
  "$PY" continuation-r8/diagnose_quantized_model-r34.py "$ROOT/qwen25-r2" "$ROOT/$RUN" > "logs/$RUN.log" 2>&1
 else
  if [ "$0" = r33 ];then export LLM_BLOCK_SCALES=1;else unset LLM_BLOCK_SCALES;fi
  RUN="firstbad-qwen25-$0-r34";mkdir "$RUN"
  sha256sum "systemc-src-$0.tar.gz" "build-$0/llm_bench" continuation-r8/diagnose_dense_layer-r34.py > "$RUN/run-inputs.sha256"
  "build-$0/llm_bench" "$ROOT/qwen25-r2" "$ROOT/$RUN" 1 > "logs/$RUN.log" 2>&1
  "$PY" continuation-r8/diagnose_dense_layer-r34.py "$ROOT/qwen25-r2" "$ROOT/$RUN" 1 >> "logs/$RUN.log" 2>&1
 fi
'
