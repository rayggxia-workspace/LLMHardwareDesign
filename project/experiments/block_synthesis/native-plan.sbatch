#!/bin/bash
#SBATCH --job-name=yzl-syn-replay
#SBATCH --partition=c64
#SBATCH --cpus-per-task=8
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/*) ;; *) exit 2;; esac
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
export PYTHONPATH="$2/deps"
cd "$root"
sha256sum *.py > source.sha256
"$python" native_plan.py "$3" "$root/generated" > generate.log 2>&1
ln -s "$3/source" "$root/source"
export SLURM_ARRAY_TASK_ID=3
bash "$root/source/project/experiments/pu_leaf_base/smoke.sh" "$root" '' "$root/generated/tb_pu_u_group.sv" > replay.log 2>&1
sha256sum generated/* replay.log > results.sha256
