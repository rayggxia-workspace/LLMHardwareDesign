#!/bin/bash
#SBATCH --job-name=yzl-sc153-dense
#SBATCH --partition=c64
#SBATCH --cpus-per-task=8
#SBATCH --time=03:00:00
set -euo pipefail
# 独立版本目录，避免覆盖另一个正在运行的可执行文件/源码。
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
REV=${1:?source revision}; CHECKPOINT=${2:?checkpoint}; RUN=${3:?run}; MODE=${4:-full}
cd "$ROOT"
mkdir -p "src-$REV" "$RUN"
tar -xzf "systemc-src-$REV.tar.gz" -C "src-$REV"
cmake -S "src-$REV/project/systemc" -B "build-$REV" -DCMAKE_PREFIX_PATH="$ROOT/install" -DCMAKE_BUILD_TYPE=Release
cmake --build "build-$REV" -j "$SLURM_CPUS_PER_TASK"
ctest --test-dir "build-$REV" --output-on-failure
sha256sum "systemc-src-$REV.tar.gz" "build-$REV/llm_bench" > "$RUN/run-inputs.sha256"
PY=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK MKL_NUM_THREADS=$SLURM_CPUS_PER_TASK
if [ "$MODE" = diagnostic ]; then
  LLM_FIRST_LAYER_ONLY=1 "build-$REV/llm_bench" "$ROOT/$CHECKPOINT" "$ROOT/$RUN" 1
  "$PY" "src-$REV/project/systemc/llm/tools/diagnose_layer.py" "$ROOT/$CHECKPOINT" "$ROOT/$RUN"
else
  "build-$REV/llm_bench" "$ROOT/$CHECKPOINT" "$ROOT/$RUN"
  "$PY" "src-$REV/project/systemc/llm/tools/validate_inference.py" "$ROOT/$CHECKPOINT" "$ROOT/$RUN"
fi
