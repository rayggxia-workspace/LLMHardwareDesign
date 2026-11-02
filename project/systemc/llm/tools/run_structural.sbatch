#!/bin/bash
#SBATCH --job-name=yzl-sc153-struct
#SBATCH --partition=debug
#SBATCH --cpus-per-task=4
#SBATCH --time=00:30:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
cd "$ROOT"
mkdir structural-r10
cd structural-r10
tar -xzf ../systemc-src-r10.tar.gz
cmake -S project/systemc -B build -DCMAKE_PREFIX_PATH="$ROOT/install" -DCMAKE_BUILD_TYPE=Release
cmake --build build -j4
ctest --test-dir build --output-on-failure
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 SC_EXPORT_THREADS=1 SLURM_CPUS_PER_TASK=1
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
PY=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PY
printf '%s\n' phi3 gemma3_text qwen3_5_text falcon_h1 | xargs -n1 -P4 bash -c '
  set -euo pipefail
  exec >"$0-fixture.log" 2>&1
  "$PY" project/systemc/llm/tools/structural_fixture.py "$0" "$0-source"
  "$PY" project/systemc/llm/tools/export_remaining.py --model "$0-source" --out "$0-cp" --new-tokens 3
  mkdir "$0-run"
  build/llm_bench "$0-cp" "$0-run"
  "$PY" project/systemc/llm/tools/validate_inference.py "$0-cp" "$0-run"
'
