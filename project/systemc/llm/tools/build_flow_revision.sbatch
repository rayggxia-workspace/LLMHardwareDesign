#!/bin/bash
#SBATCH --job-name=yzl-sc153-flow-build
#SBATCH --partition=c64
#SBATCH --nodelist=node3
#SBATCH --cpus-per-task=8
#SBATCH --time=00:30:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
REV=${1:?revision};cd "$ROOT"
mkdir "src-$REV";tar -xzf "systemc-src-$REV.tar.gz" -C "src-$REV"
cmake -S "src-$REV/project/systemc" -B "build-$REV" -DCMAKE_PREFIX_PATH="$ROOT/install" -DCMAKE_BUILD_TYPE=Release
cmake --build "build-$REV" -j8
ctest --test-dir "build-$REV" --output-on-failure
sha256sum "systemc-src-$REV.tar.gz" "build-$REV/llm_bench"
