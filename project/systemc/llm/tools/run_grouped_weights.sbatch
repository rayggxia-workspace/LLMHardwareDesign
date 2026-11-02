#!/bin/bash
#SBATCH --job-name=yzl-sc153-grouped-weights
#SBATCH --partition=c64
#SBATCH --nodelist=node1
#SBATCH --cpus-per-task=8
#SBATCH --time=01:00:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
REV=${1:-r28}
cd "$ROOT"
mkdir "src-$REV"
tar -xzf "systemc-src-$REV.tar.gz" -C "src-$REV"
cmake -S "src-$REV/project/systemc" -B "build-$REV" -DCMAKE_PREFIX_PATH="$ROOT/install" -DCMAKE_BUILD_TYPE=Release
cmake --build "build-$REV" -j8
ctest --test-dir "build-$REV" --output-on-failure
awk '/MemAvailable/ {print; if ($2 < 120*1024*1024) exit 1}' /proc/meminfo
export ROOT REV
printf '%s\n' phi3-fixture gemma3_text-fixture qwen3_5_text-fixture falcon_h1-fixture phi gemma qwen35 falcon qwen3 qwen25 granite | xargs -n1 -P6 bash -c '
 set -euo pipefail
 export SLURM_CPUS_PER_TASK=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
 export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 LLM_PRECISE_ADAPTER=1
 unset LLM_NORM_FUSED LLM_FIRST_LAYER_ONLY LLM_TRACE_LAYER
 MODEL=$0;CP="$MODEL-g8-$REV";OLD="$MODEL-r8";RUN="run-$MODEL-$REV"
 case "$MODEL" in
  *-fixture) FAMILY=${MODEL%-fixture};OLD="structural-r10/$FAMILY-cp";;
  qwen3) OLD=qwen3-r2;export LLM_TRACE_LAYER=27;;
  qwen25) OLD=qwen25-r2;export LLM_TRACE_LAYER=30;;
  granite) OLD=granite-r1;;
  phi) export LLM_TRACE_LAYER=30;;
  gemma) export LLM_TRACE_LAYER=33;;
  falcon) OLD=falcon-old-scale-r22;export LLM_TRACE_SSM=1;;
 esac
 PY=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
 exec >"logs/$RUN.log" 2>&1
 if [ "$MODEL" = falcon_h1-fixture ];then
  "$PY" "src-$REV/project/systemc/llm/tools/repair_falcon_metadata.py" "$ROOT/$OLD" "$ROOT/falcon-fixture-base-$REV"
  OLD="falcon-fixture-base-$REV"
 fi
 "$PY" "src-$REV/project/systemc/llm/tools/requantize_groups.py" "$ROOT/$OLD" "$ROOT/$CP"
 mkdir "$RUN"
 sha256sum "systemc-src-$REV.tar.gz" "build-$REV/llm_bench" "$CP/metadata.txt" "$CP/weights.index" "$CP/weights.scales" > "$RUN/run-inputs.sha256"
 "build-$REV/llm_bench" "$ROOT/$CP" "$ROOT/$RUN"
 "$PY" "src-$REV/project/systemc/llm/tools/validate_inference.py" "$ROOT/$CP" "$ROOT/$RUN"
'
