#!/bin/bash
#SBATCH --job-name=yzl-sc153-staticseq
#SBATCH --partition=c64
#SBATCH --nodelist=node5
#SBATCH --cpus-per-task=8
#SBATCH --time=02:00:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
cd "$ROOT";export ROOT
awk '/MemAvailable/ {print; if ($2 < 120*1024*1024) exit 1}' /proc/meminfo
printf '%s\n' gemma falcon qwen25 phi qwen3 qwen35 granite | xargs -n1 -P6 bash -c '
 set -euo pipefail
 export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 SLURM_CPUS_PER_TASK=1 PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
 PY=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
 MODEL=$0;RUN="run-$MODEL-f14-sequence";TOOLS="$ROOT/src-f14/project/systemc/llm/tools"
 case "$MODEL" in gemma|falcon) CP="sequence-$MODEL-f14";;qwen25) CP=sequence-qwen25-f7;;*) CP="sequence-$MODEL-f4";;esac
 exec >"logs/$RUN.log" 2>&1
 mkdir "$RUN"
 export LLM_PRECISE_ADAPTER=1 LLM_BLOCK_SCALES=1 LLM_ACCURATE_SILU=1 LLM_LINK=1 LLM_LINK_WIDTH_BYTES=64 LLM_LINK_QUEUE_PACKETS=1 LLM_FLOW_DIR="$ROOT/$RUN"
 unset LLM_LINK_CORRUPT LLM_LINK_DROP_RESPONSE LLM_FIRST_LAYER_ONLY LLM_TRACE_LAYER LLM_NORM_FUSED LLM_SSM_BLOCK_SCALES
 sha256sum systemc-src-f14.tar.gz build-f14/llm_bench continuation-r8/final-sequence-f14.sbatch "$CP/metadata.txt" "$CP/weights.index" > "$RUN/run-inputs.sha256"
 for n in weights.scales parameters.scales;do if [[ -f "$CP/$n" ]];then sha256sum "$CP/$n" >> "$RUN/run-inputs.sha256";fi;done
 build-f14/llm_bench "$ROOT/$CP" "$ROOT/$RUN"
 case "$MODEL" in gemma|falcon) :;;*)
  if [[ "$MODEL" == qwen25 ]];then BASE=run-qwen25-f7-sequence;else BASE="run-$MODEL-f4-sequence";fi
  cmp "$RUN/systemc_hidden.bin" "$BASE/systemc_hidden.bin";cmp "$RUN/systemc_logits.bin" "$BASE/systemc_logits.bin";;esac
 python3 "$TOOLS/analyze_flow.py" "$RUN"
 "$PY" "$TOOLS/validate_inference.py" "$CP" "$RUN"
 python3 "$TOOLS/assess_numerics.py" "$RUN/validation.json" --out "$RUN/numerical-gates.json"
'
