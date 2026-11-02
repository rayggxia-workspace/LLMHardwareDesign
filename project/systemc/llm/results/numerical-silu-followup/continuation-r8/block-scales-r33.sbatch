#!/bin/bash
#SBATCH --job-name=yzl-sc153-block-scales
#SBATCH --partition=c64
#SBATCH --nodelist=node1
#SBATCH --cpus-per-task=8
#SBATCH --time=02:00:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
REV=${1:-r33}
cd "$ROOT"
mkdir "src-$REV"
tar -xzf "systemc-src-$REV.tar.gz" -C "src-$REV"
cmake -S "src-$REV/project/systemc" -B "build-$REV" -DCMAKE_PREFIX_PATH="$ROOT/install" -DCMAKE_BUILD_TYPE=Release
cmake --build "build-$REV" -j8
ctest --test-dir "build-$REV" --output-on-failure
# At most six live independent one-thread tasks; measured node1 free memory
# exceeded437GiB. Reserve120GiB headroom for integer weights and FP32 replays.
awk '/MemAvailable/ {print; if ($2 < 120*1024*1024) exit 1}' /proc/meminfo
export ROOT REV
printf '%s\n' phi gemma qwen35 falcon qwen3 qwen25 granite | xargs -n1 -P6 bash -c '
  set -euo pipefail
  export SLURM_CPUS_PER_TASK=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
  export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
  unset LLM_NORM_FUSED LLM_TRACE_LAYER LLM_FIRST_LAYER_ONLY
  export LLM_PRECISE_ADAPTER=1 LLM_BLOCK_SCALES=1
  MODEL=$0; RUN="run-$MODEL-$REV"
  case "$MODEL" in phi|qwen25) export LLM_TRACE_LAYER=30;; qwen3) export LLM_TRACE_LAYER=27;; gemma) export LLM_TRACE_LAYER=33;; falcon) export LLM_TRACE_SSM=1;; esac
  case "$MODEL" in qwen3) CP=qwen3-r2;; qwen25) CP=qwen25-r2;; granite) CP=granite-residual-r32;; falcon) CP=falcon-old-scale-r22;; *) CP="$MODEL-r8";; esac
  mkdir "$RUN"
  exec >"logs/$RUN.log" 2>&1
  test -f "$CP/export_receipt.json"
  sha256sum "systemc-src-$REV.tar.gz" "build-$REV/llm_bench" "$CP/metadata.txt" "$CP/weights.index" > "$RUN/run-inputs.sha256"
  "build-$REV/llm_bench" "$ROOT/$CP" "$ROOT/$RUN"
  /public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python "src-$REV/project/systemc/llm/tools/validate_inference.py" "$ROOT/$CP" "$ROOT/$RUN"
'
