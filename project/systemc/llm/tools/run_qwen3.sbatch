#!/bin/bash
#SBATCH --job-name=yzl-sc153-infer
#SBATCH --partition=c64
#SBATCH --cpus-per-task=8
#SBATCH --time=03:00:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
cd "$ROOT"
test "$(sha256sum systemc.tar.gz | cut -d' ' -f1)" = d07765d0d2ffd6c01767880d0c6aaf53cd9487975f898c593ffffd713258fcbb
if [ ! -f install/lib/libsystemc.so ]; then
  mkdir -p deps
  tar -xzf systemc.tar.gz -C deps
  cmake -S deps/systemc-3.0.1 -B deps/build -DCMAKE_INSTALL_PREFIX="$ROOT/install" -DCMAKE_CXX_STANDARD=17 -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON
  cmake --build deps/build -j "$SLURM_CPUS_PER_TASK"
  cmake --install deps/build
fi
tar -xzf systemc-src.tar.gz -C src
cmake -S src/project/systemc -B build -DCMAKE_PREFIX_PATH="$ROOT/install" -DCMAKE_BUILD_TYPE=Release
cmake --build build -j "$SLURM_CPUS_PER_TASK"
ctest --test-dir build --output-on-failure
mkdir -p run-qwen3-r1
build/llm_bench "$ROOT/qwen3-r1" "$ROOT/run-qwen3-r1"

/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python "$ROOT/src/project/systemc/llm/tools/validate_inference.py" "$ROOT/qwen3-r1" "$ROOT/run-qwen3-r1"
