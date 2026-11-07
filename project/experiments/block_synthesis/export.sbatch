#!/bin/bash
#SBATCH --job-name=yzl-syn-3b
#SBATCH --partition=c64
#SBATCH --cpus-per-task=8
#SBATCH --time=0
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/*) ;; *) exit 2;; esac
export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK OPENBLAS_NUM_THREADS=$SLURM_CPUS_PER_TASK MKL_NUM_THREADS=$SLURM_CPUS_PER_TASK
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/public/home/yuzelu/project-circuit/LLMHardwareDesign/operator-graphs-20261026/deps
python=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python
sha256sum "$root/export_model.py" "$2/config.json" "$2/"*.safetensors > "$root/input.sha256"
"$python" -u "$root/export_model.py" "$2" "$root/complete" > "$root/export.log" 2>&1
sha256sum "$root/complete/"*.onnx "$root/complete/receipt.json" > "$root/output.sha256"
