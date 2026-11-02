#!/bin/bash
#SBATCH --job-name=yzl-sc153-run8
#SBATCH --partition=c64
#SBATCH --cpus-per-task=8
#SBATCH --time=02:00:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
REV=${1:-r8}
cd "$ROOT"
mkdir "src-$REV"
tar -xzf "systemc-src-$REV.tar.gz" -C "src-$REV"
cmake -S "src-$REV/project/systemc" -B "build-$REV" -DCMAKE_PREFIX_PATH="$ROOT/install" -DCMAKE_BUILD_TYPE=Release
cmake --build "build-$REV" -j8
ctest --test-dir "build-$REV" --output-on-failure
awk '/MemAvailable/ {if ($2 < 120*1024*1024) exit 1}' /proc/meminfo
# Four independent one-thread simulators. Completed models free their slots immediately.
export ROOT REV
printf '%s\n' phi gemma qwen35 falcon | xargs -n1 -P4 bash -c '
  set -euo pipefail
  export SLURM_CPUS_PER_TASK=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
  export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
  MODEL=$0; RUN="run-$MODEL-$REV"; CP="$MODEL-r8"
  mkdir "$RUN"
  exec >"logs/$RUN.log" 2>&1
  test -f "$CP/export_receipt.json"
  sha256sum "systemc-src-$REV.tar.gz" "build-$REV/llm_bench" "$CP/metadata.txt" "$CP/weights.index" > "$RUN/run-inputs.sha256"
  "build-$REV/llm_bench" "$ROOT/$CP" "$ROOT/$RUN"
  /public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python "src-$REV/project/systemc/llm/tools/validate_inference.py" "$ROOT/$CP" "$ROOT/$RUN"
'
