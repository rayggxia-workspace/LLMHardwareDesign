#!/bin/bash
#SBATCH --job-name=yzl-sc153-flow
#SBATCH --partition=c64
#SBATCH --nodelist=node2
#SBATCH --cpus-per-task=8
#SBATCH --time=02:00:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
REV=${1:?revision};MODE=${2:-trace}
cd "$ROOT"
if [ "$MODE" = trace ];then
 mkdir "src-$REV"
 tar -xzf "systemc-src-$REV.tar.gz" -C "src-$REV"
 cmake -S "src-$REV/project/systemc" -B "build-$REV" -DCMAKE_PREFIX_PATH="$ROOT/install" -DCMAKE_BUILD_TYPE=Release
 cmake --build "build-$REV" -j8
 ctest --test-dir "build-$REV" --output-on-failure
fi
awk '/MemAvailable/ {print; if ($2 < 120*1024*1024) exit 1}' /proc/meminfo
export ROOT REV MODE
printf '%s\n' phi gemma qwen35 falcon qwen3 qwen25 granite | xargs -n1 -P6 bash -c '
 set -euo pipefail
 export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 SLURM_CPUS_PER_TASK=1 PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
 export LLM_PRECISE_ADAPTER=1 LLM_BLOCK_SCALES=1 LLM_ACCURATE_SILU=1
 unset LLM_LINK LLM_LINK_DROP_RESPONSE LLM_LINK_CORRUPT LLM_NORM_FUSED LLM_FIRST_LAYER_ONLY LLM_TRACE_LAYER
 MODEL=$0;RUN="run-$MODEL-$REV-$MODE"
 case "$MODEL" in qwen3) CP=qwen3-r2;; qwen25) CP=qwen25-r2;; granite) CP=granite-residual-r32;; falcon) CP=falcon-old-scale-r22;; *) CP="$MODEL-r8";; esac
 mkdir "$RUN";export LLM_FLOW_DIR="$ROOT/$RUN"
 case "$MODE" in trace) ;;
  narrow) export LLM_LINK=1 LLM_LINK_WIDTH_BYTES=16 LLM_LINK_QUEUE_PACKETS=1;;
  wide) export LLM_LINK=1 LLM_LINK_WIDTH_BYTES=64 LLM_LINK_QUEUE_PACKETS=4;;
  wide1) export LLM_LINK=1 LLM_LINK_WIDTH_BYTES=64 LLM_LINK_QUEUE_PACKETS=1;;
  *) exit 2;;esac
 exec >"logs/$RUN.log" 2>&1
 sha256sum "systemc-src-$REV.tar.gz" "build-$REV/llm_bench" "$CP/metadata.txt" "$CP/weights.index" > "$RUN/run-inputs.sha256"
 "build-$REV/llm_bench" "$ROOT/$CP" "$ROOT/$RUN"
 cmp "$RUN/systemc_hidden.bin" "run-$MODEL-r35/systemc_hidden.bin"
 cmp "$RUN/systemc_logits.bin" "run-$MODEL-r35/systemc_logits.bin"
 python3 "src-$REV/project/systemc/llm/tools/analyze_flow.py" "$RUN"
 /public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python "src-$REV/project/systemc/llm/tools/validate_inference.py" "$CP" "$RUN"
 python3 "src-$REV/project/systemc/llm/tools/assess_numerics.py" "$RUN/validation.json" --out "$RUN/numerical-gates.json"
'
