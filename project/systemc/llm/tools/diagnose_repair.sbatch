#!/bin/bash
#SBATCH --job-name=yzl-sc153-diag14
#SBATCH --partition=c64
#SBATCH --nodelist=node1
#SBATCH --cpus-per-task=8
#SBATCH --time=01:00:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
REV=${1:-r14}
cd "$ROOT"
mkdir "src-$REV"
tar -xzf "systemc-src-$REV.tar.gz" -C "src-$REV"
cmake -S "src-$REV/project/systemc" -B "build-$REV" -DCMAKE_PREFIX_PATH="$ROOT/install" -DCMAKE_BUILD_TYPE=Release
cmake --build "build-$REV" -j8
ctest --test-dir "build-$REV" --output-on-failure
export ROOT REV
printf '%s\n' phi qwen25 qwen3 gemma falcon | xargs -n1 -P5 bash -c '
 set -euo pipefail
 export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 SLURM_CPUS_PER_TASK=1 PYTHONDONTWRITEBYTECODE=1
 export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
 unset LLM_NORM_FUSED LLM_FIRST_LAYER_ONLY
 MODEL=$0;CP="$MODEL-r8"
 case "$MODEL" in phi) LAYER=30;; qwen25) CP=qwen25-r2;LAYER=30;; qwen3) CP=qwen3-r2;LAYER=27;; gemma) LAYER=33;; falcon) LAYER=0;; esac
 export LLM_TRACE_LAYER=$LAYER LLM_TRACE_SSM=1
 RUN="diag-$MODEL-$REV";mkdir "$RUN"
 exec >"logs/$RUN.log" 2>&1
 sha256sum "systemc-src-$REV.tar.gz" "build-$REV/llm_bench" > "$RUN/run-inputs.sha256"
 "build-$REV/llm_bench" "$ROOT/$CP" "$ROOT/$RUN" 1
 if [ "$MODEL" != falcon ]; then
 /public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python "src-$REV/project/systemc/llm/tools/diagnose_dense_layer.py" "$ROOT/$CP" "$ROOT/$RUN" "$LAYER"
 fi
'
