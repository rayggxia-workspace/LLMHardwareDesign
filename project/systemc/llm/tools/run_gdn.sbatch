#!/bin/bash
#SBATCH --job-name=yzl-sc153-gdn
#SBATCH --partition=c64
#SBATCH --cpus-per-task=8
#SBATCH --time=00:30:00
set -euo pipefail
export ROOT=/public/home/yuzelu/project-circuit/LLMHardwareDesign/systemc-llm-issue153
export PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK MKL_NUM_THREADS=$SLURM_CPUS_PER_TASK
cd "$ROOT"
mkdir -p src-r6g
tar -xzf systemc-src-r6g.tar.gz -C src-r6g
TOOLS="$ROOT/src-r6g/project/systemc/llm/tools"
PY=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
if [ ! -f gdn-boundary-r2/export_receipt.json ]; then
  "$PY" "$TOOLS/export_gdn.py"
fi
# 该服务器缺失libubsan.so；本地WSL另执行UBSan，远程不伪称已启用。
cmake -S src-r6g/project/systemc -B build-r6g -DCMAKE_PREFIX_PATH="$ROOT/install" -DCMAKE_BUILD_TYPE=Release -DBLOCK_SANITIZE=OFF
cmake --build build-r6g -j "$SLURM_CPUS_PER_TASK"
ctest --test-dir build-r6g --output-on-failure
build-r6g/gdn_bench "$ROOT/gdn-boundary-r2"
"$PY" "$TOOLS/validate_gdn.py" "$ROOT/gdn-boundary-r2"
sha256sum systemc-src-r6g.tar.gz build-r6g/gdn_bench > gdn-boundary-r2/run-inputs.sha256
