#!/bin/bash
#SBATCH --job-name=yzl-sc153-staticlinks
#SBATCH --partition=c64
#SBATCH --nodelist=node6
#SBATCH --cpus-per-task=8
#SBATCH --time=02:00:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
cd "$ROOT";export ROOT
awk '/MemAvailable/ {print; if ($2 < 120*1024*1024) exit 1}' /proc/meminfo
printf '%s\n' gemma-narrow gemma-wide1 gemma-wide falcon-narrow falcon-wide1 falcon-wide qwen25-wide1 | xargs -n1 -P6 bash -c '
 set -euo pipefail
 export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 SLURM_CPUS_PER_TASK=1 PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
 PY=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
 TASK=$0;MODEL=${TASK%%-*};MODE=${TASK#*-};RUN="run-$TASK-f15";CP="recheck-$TASK-f15";TOOLS="$ROOT/src-f14/project/systemc/llm/tools"
 exec >"logs/$RUN.log" 2>&1
 case "$MODEL" in gemma) WEIGHTS=sequence-gemma-f14;OLD=gemma-r8;;falcon) WEIGHTS=sequence-falcon-f14;OLD=falcon-old-scale-r22;;qwen25) WEIGHTS=sequence-qwen25-f7;OLD=qwen25-r2;;esac
 python3 "$TOOLS/prepare_short_recheck.py" "$ROOT/$WEIGHTS" "$ROOT/$OLD" "$ROOT/$CP"
 mkdir "$RUN"
 export LLM_PRECISE_ADAPTER=1 LLM_BLOCK_SCALES=1 LLM_ACCURATE_SILU=1 LLM_LINK=1 LLM_LINK_WIDTH_BYTES=64 LLM_LINK_QUEUE_PACKETS=1 LLM_FLOW_DIR="$ROOT/$RUN"
 if [[ "$MODE" == narrow ]];then export LLM_LINK_WIDTH_BYTES=16;fi
 if [[ "$MODE" == wide ]];then export LLM_LINK_QUEUE_PACKETS=4;fi
 unset LLM_LINK_CORRUPT LLM_LINK_DROP_RESPONSE LLM_FIRST_LAYER_ONLY LLM_TRACE_LAYER LLM_NORM_FUSED LLM_SSM_BLOCK_SCALES
 sha256sum systemc-src-f14.tar.gz build-f14/llm_bench continuation-r8/final-short-links-f15.sbatch "$TOOLS/prepare_short_recheck.py" "$CP/metadata.txt" "$CP/weights.index" > "$RUN/run-inputs.sha256"
 for n in weights.scales parameters.scales;do if [[ -f "$CP/$n" ]];then sha256sum "$CP/$n" >> "$RUN/run-inputs.sha256";fi;done
 build-f14/llm_bench "$ROOT/$CP" "$ROOT/$RUN"
 python3 "$TOOLS/analyze_flow.py" "$RUN"
 "$PY" "$TOOLS/validate_inference.py" "$CP" "$RUN"
 python3 "$TOOLS/assess_numerics.py" "$RUN/validation.json" --out "$RUN/numerical-gates.json"
'
