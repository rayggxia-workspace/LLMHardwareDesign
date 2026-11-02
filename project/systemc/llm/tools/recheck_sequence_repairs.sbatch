#!/bin/bash
#SBATCH --job-name=yzl-sc153-seqrecheck
#SBATCH --partition=c64
#SBATCH --nodelist=node6
#SBATCH --cpus-per-task=8
#SBATCH --time=02:00:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
cd "$ROOT";export ROOT
printf '%s\n' gemma-long qwen25-long gemma-short qwen25-short falcon-short falcon-narrow falcon-wide | xargs -n1 -P6 bash -c '
 set -euo pipefail
 export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 SLURM_CPUS_PER_TASK=1 PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
 PY=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
 TASK=$0;MODEL=${TASK%%-*};KIND=${TASK#*-};RUN="run-$TASK-f9"
 exec >"logs/$RUN.log" 2>&1
 case "$MODEL" in gemma) W=sequence-gemma-f7;OLD=gemma-r8;;qwen25) W=sequence-qwen25-f7;OLD=qwen25-r2;;falcon) W=sequence-falcon-f8;OLD=falcon-old-scale-r22;;esac
 if [[ "$KIND" == long ]];then CP=$W;else
  CP="recheck-$TASK-f9"
  python3 continuation-r8/prepare-short-recheck-f9.py "$ROOT/$W" "$ROOT/$OLD" "$ROOT/$CP"
 fi
 mkdir "$RUN"
 export LLM_PRECISE_ADAPTER=1 LLM_BLOCK_SCALES=1 LLM_ACCURATE_SILU=1 LLM_LINK=1 LLM_LINK_WIDTH_BYTES=64 LLM_LINK_QUEUE_PACKETS=1 LLM_FLOW_DIR="$ROOT/$RUN"
 if [[ "$KIND" == narrow ]];then export LLM_LINK_WIDTH_BYTES=16;fi
 if [[ "$KIND" == wide ]];then export LLM_LINK_QUEUE_PACKETS=4;fi
 unset LLM_LINK_CORRUPT LLM_LINK_DROP_RESPONSE LLM_FIRST_LAYER_ONLY LLM_TRACE_LAYER LLM_NORM_FUSED LLM_SSM_BLOCK_SCALES
 sha256sum systemc-src-f2.tar.gz build-f2/llm_bench continuation-r8/sequence-recheck-f9.sbatch continuation-r8/prepare-short-recheck-f9.py "$CP/metadata.txt" "$CP/weights.index" "$CP/weights.scales" > "$RUN/run-inputs.sha256"
 build-f2/llm_bench "$ROOT/$CP" "$ROOT/$RUN"
 if [[ "$KIND" == long ]];then
  cmp "$RUN/systemc_hidden.bin" "run-$MODEL-f7-sequence/systemc_hidden.bin"
  cmp "$RUN/systemc_logits.bin" "run-$MODEL-f7-sequence/systemc_logits.bin"
 fi
 python3 src-f2/project/systemc/llm/tools/analyze_flow.py "$RUN"
 "$PY" src-f2/project/systemc/llm/tools/validate_inference.py "$CP" "$RUN"
 python3 src-f2/project/systemc/llm/tools/assess_numerics.py "$RUN/validation.json" --out "$RUN/numerical-gates.json"
'
