#!/bin/bash
#SBATCH --job-name=yzl-syn-rows
#SBATCH --partition=c64
#SBATCH --cpus-per-task=8
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
envroot=$(realpath "$2")
qual=$(realpath "$3")
memory_source=$(realpath "$4")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/algorithm-fix-*) ;; *) exit 2;; esac
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$envroot/deps${PYTHONPATH:+:$PYTHONPATH}"
cd "$root"
sha256sum *.py "$memory_source" > input.sha256
"$python" -B native_rows.py "$qual" "$memory_source" "$root/result" > generation.log 2>&1
cp -a "$qual/source" "$root/source"
export SLURM_ARRAY_TASK_ID=3
bash "$root/source/project/experiments/pu_leaf_base/smoke.sh" "$root" '' "$root/result/tb_pu_u_group.sv" > native.log 2>&1
test "$(grep -c NATIVE_ROWS_PASS native.log)" = 3
sha256sum result/* generation.log native.log > output.sha256
