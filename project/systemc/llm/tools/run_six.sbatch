#!/bin/bash
#SBATCH --job-name=yzl-sc153-six
#SBATCH --partition=c64
#SBATCH --cpus-per-task=8
#SBATCH --time=02:00:00
set -euo pipefail
ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
cd "$ROOT";mkdir -p src-r6
tar -xzf systemc-src-r6.tar.gz -C src-r6
cmake -S src-r6/project/systemc -B build-r6 -DCMAKE_PREFIX_PATH="$ROOT/install" -DCMAKE_BUILD_TYPE=Release
cmake --build build-r6 -j "$SLURM_CPUS_PER_TASK"
ctest --test-dir build-r6 --output-on-failure
# 真实MemAvailable用于限制内存并发，不使用集群不准确的1MiB Slurm元数据。
# 每个独立任务预留10GiB；每任务模拟器单线程，验证torch也仅1线程。
available_kib=$(awk '/MemAvailable:/{print $2}' /proc/meminfo)
parallel=$((available_kib / 10485760)); [ "$parallel" -ge 1 ] || parallel=1
[ "$parallel" -le 6 ] || parallel=6
echo "MemAvailableKiB=$available_kib independent_tasks=$parallel allocation_cpus=$SLURM_CPUS_PER_TASK"
printf '%s\n' 'qwen3-r2 run-qwen3-r6 unit' 'qwen25-r2 run-qwen25-r6 unit' 'granite-r1 run-granite-r6 unit' 'qwen3-r2 run-qwen3-r6-fused fused' 'qwen25-r2 run-qwen25-r6-fused fused' 'granite-r1 run-granite-r6-fused fused' |
  xargs -r -n3 -P "$parallel" bash src-r6/project/systemc/llm/tools/run_one.sh
