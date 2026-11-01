#!/bin/bash
#SBATCH --job-name=yzl-sc153-seqrepair
#SBATCH --partition=c64
#SBATCH --nodelist=node3
#SBATCH --cpus-per-task=8
#SBATCH --time=02:00:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
REV=${1:?revision};cd "$ROOT";export ROOT REV
mkdir "src-$REV";tar -xzf "systemc-src-$REV.tar.gz" -C "src-$REV"
cmake -S "src-$REV/project/systemc" -B "build-$REV" -DCMAKE_PREFIX_PATH="$ROOT/install" -DCMAKE_BUILD_TYPE=Release
cmake --build "build-$REV" -j8
ctest --test-dir "build-$REV" --output-on-failure
printf '%s\n' diag-falcon diag-gemma diag-qwen25 falcon-sequence falcon-short | xargs -n1 -P6 bash -c '
 set -euo pipefail
 export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 SLURM_CPUS_PER_TASK=1 PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
 PY=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
 TOOLS="$ROOT/src-$REV/project/systemc/llm/tools";TASK=$0
 exec >"$ROOT/logs/sequence-repair-$REV-$TASK.log" 2>&1
 if [[ "$TASK" == diag-* ]];then
  MODEL=${TASK#diag-}
  "$PY" "$TOOLS/diagnose_quantized_model.py" "$ROOT/sequence-$MODEL-f4" "$ROOT/run-$MODEL-f4-sequence" --out "$ROOT/sequence-diagnostic-$MODEL-$REV.json"
 else
  if [[ "$TASK" == falcon-sequence ]];then CP=sequence-falcon-f4;else CP=falcon-old-scale-r22;fi
  RUN="run-$TASK-$REV";mkdir "$RUN"
  export LLM_PRECISE_ADAPTER=1 LLM_BLOCK_SCALES=1 LLM_ACCURATE_SILU=1 LLM_SSM_BLOCK_SCALES=1 LLM_LINK=1 LLM_LINK_WIDTH_BYTES=64 LLM_LINK_QUEUE_PACKETS=1 LLM_FLOW_DIR="$ROOT/$RUN"
  unset LLM_LINK_CORRUPT LLM_LINK_DROP_RESPONSE LLM_FIRST_LAYER_ONLY LLM_TRACE_LAYER LLM_NORM_FUSED
  sha256sum "systemc-src-$REV.tar.gz" "build-$REV/llm_bench" "continuation-r8/sequence-repair-$REV.sbatch" "$CP/metadata.txt" "$CP/weights.index" > "$RUN/run-inputs.sha256"
  "build-$REV/llm_bench" "$ROOT/$CP" "$ROOT/$RUN"
  python3 "$TOOLS/analyze_flow.py" "$RUN"
  "$PY" "$TOOLS/validate_inference.py" "$CP" "$RUN"
  python3 "$TOOLS/assess_numerics.py" "$RUN/validation.json" --out "$RUN/numerical-gates.json"
 fi
'
