#!/bin/bash
#SBATCH --job-name=yzl-sc153-sequence
#SBATCH --partition=c64
#SBATCH --nodelist=node5
#SBATCH --cpus-per-task=8
#SBATCH --time=02:00:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
cd "$ROOT";export ROOT
awk '/MemAvailable/ {print; if ($2 < 120*1024*1024) exit 1}' /proc/meminfo
printf '%s\n' phi gemma qwen35 falcon qwen3 qwen25 granite | xargs -n1 -P6 bash -c '
 set -euo pipefail
 export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 SLURM_CPUS_PER_TASK=1 PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
 export LLM_PRECISE_ADAPTER=1 LLM_BLOCK_SCALES=1 LLM_ACCURATE_SILU=1
 unset LLM_LINK_CORRUPT LLM_LINK_DROP_RESPONSE LLM_FIRST_LAYER_ONLY LLM_TRACE_LAYER LLM_NORM_FUSED
 PY=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
 MODEL=$0;CP="sequence-$MODEL-f4";RUN="run-$MODEL-f4-sequence"
 case "$MODEL" in qwen3) OLD=qwen3-r2;; qwen25) OLD=qwen25-r2;; granite) OLD=granite-residual-r32;; falcon) OLD=falcon-old-scale-r22;; *) OLD="$MODEL-r8";; esac
 exec >"logs/$RUN.log" 2>&1
 "$PY" src-f2/project/systemc/llm/tools/prepare_sequence_case.py "$ROOT/$OLD" "$ROOT/$CP" --prompt "Hello world" --new-tokens 8
 mkdir "$RUN";export LLM_FLOW_DIR="$ROOT/$RUN"
 export LLM_LINK=1 LLM_LINK_WIDTH_BYTES=64 LLM_LINK_QUEUE_PACKETS=1
 sha256sum systemc-src-f2.tar.gz build-f2/llm_bench src-f2/project/systemc/llm/tools/prepare_sequence_case.py continuation-r8/sequence-suite-f4.sbatch "$CP/metadata.txt" "$CP/weights.index" > "$RUN/run-inputs.sha256"
 build-f2/llm_bench "$ROOT/$CP" "$ROOT/$RUN"
 python3 src-f2/project/systemc/llm/tools/analyze_flow.py "$RUN"
 "$PY" src-f2/project/systemc/llm/tools/validate_inference.py "$CP" "$RUN"
 python3 src-f2/project/systemc/llm/tools/assess_numerics.py "$RUN/validation.json" --out "$RUN/numerical-gates.json"
'
