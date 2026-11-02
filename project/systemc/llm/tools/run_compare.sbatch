#!/bin/bash
#SBATCH --job-name=yzl-sc153-compare
#SBATCH --partition=c64
#SBATCH --cpus-per-task=8
#SBATCH --time=02:00:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
REV=${1:-r7};cd "$ROOT";mkdir -p "src-$REV"
tar -xzf "systemc-src-$REV.tar.gz" -C "src-$REV"
cmake -S "src-$REV/project/systemc" -B "build-$REV" -DCMAKE_PREFIX_PATH="$ROOT/install" -DCMAKE_BUILD_TYPE=Release
cmake --build "build-$REV" -j "$SLURM_CPUS_PER_TASK"
ctest --test-dir "build-$REV" --output-on-failure
printf 'qwen3-r2 run-qwen3-%s-fused fused %s\nqwen25-r2 run-qwen25-%s-fused fused %s\ngranite-r1 run-granite-%s-fused fused %s\n' "$REV" "$REV" "$REV" "$REV" "$REV" "$REV" |
  xargs -r -n4 -P3 bash "src-$REV/project/systemc/llm/tools/run_one.sh"
