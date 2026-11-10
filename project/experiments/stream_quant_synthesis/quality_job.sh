#!/usr/bin/env bash
#SBATCH --job-name=yl-sq-quality
#SBATCH --partition=c64,c96
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=0
#SBATCH --output=quality-slurm-%j.log
set -euo pipefail
root=$SLURM_SUBMIT_DIR
cd "$root/source"
sha256sum -c "$root/source-files.sha256" > "$root/quality-source-check.log"
cd "$root"
scontrol show job "$SLURM_JOB_ID" > quality-allocation.txt
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1
export TORCH_HOME="$root/torch-cache"
exec srun --exact -n1 -c4 --cpu-bind=cores \
 /public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python -B \
 "$root/source/project/experiments/stream_quant_synthesis/quality.py" \
 --checkpoint /public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/models/qwen25-3b-5defd279 \
 --out "$root/quality" --weight-policy linear
