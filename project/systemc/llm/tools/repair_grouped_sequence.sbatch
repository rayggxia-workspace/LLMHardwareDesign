#!/bin/bash
#SBATCH --job-name=yzl-sc153-seqweights
#SBATCH --partition=c64
#SBATCH --nodelist=node4
#SBATCH --cpus-per-task=4
#SBATCH --time=02:00:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
cd "$ROOT";export ROOT
printf '%s\n' gemma qwen25 | xargs -n1 -P2 bash -c '
 set -euo pipefail
 export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 SLURM_CPUS_PER_TASK=1 PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
 PY=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
 TOOLS="$ROOT/src-f6/project/systemc/llm/tools";MODEL=$0;CP="sequence-$MODEL-f7";RUN="run-$MODEL-f7-sequence"
 exec >"logs/$RUN.log" 2>&1
 "$PY" "$TOOLS/requantize_groups.py" "$ROOT/sequence-$MODEL-f4" "$ROOT/$CP"
 mkdir "$RUN"
 export LLM_PRECISE_ADAPTER=1 LLM_BLOCK_SCALES=1 LLM_ACCURATE_SILU=1 LLM_LINK=1 LLM_LINK_WIDTH_BYTES=64 LLM_LINK_QUEUE_PACKETS=1 LLM_FLOW_DIR="$ROOT/$RUN"
 unset LLM_LINK_CORRUPT LLM_LINK_DROP_RESPONSE LLM_FIRST_LAYER_ONLY LLM_TRACE_LAYER LLM_NORM_FUSED LLM_SSM_BLOCK_SCALES
 sha256sum systemc-src-f6.tar.gz build-f6/llm_bench continuation-r8/sequence-weights-f7.sbatch "$CP/metadata.txt" "$CP/weights.index" "$CP/weights.scales" > "$RUN/run-inputs.sha256"
 build-f6/llm_bench "$ROOT/$CP" "$ROOT/$RUN"
 python3 "$TOOLS/analyze_flow.py" "$RUN"
 "$PY" "$TOOLS/validate_inference.py" "$CP" "$RUN"
 python3 "$TOOLS/assess_numerics.py" "$RUN/validation.json" --out "$RUN/numerical-gates.json"
'
