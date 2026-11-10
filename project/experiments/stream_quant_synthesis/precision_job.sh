#!/usr/bin/env bash
#SBATCH --job-name=yl-sq-precision
#SBATCH --partition=c64,c96
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=0
#SBATCH --output=precision-slurm-%j.log
set -euo pipefail
root=$SLURM_SUBMIT_DIR
cd "$root/source"
sha256sum -c "$root/source-files.sha256" > "$root/source-check.log"
cd "$root"
scontrol show job "$SLURM_JOB_ID" > allocation.txt
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 MKL_NUM_THREADS=4
export TORCH_HOME="$root/torch-cache"
srun --exact -n1 -c4 --cpu-bind=cores \
 /public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/venv-modern/bin/python -B \
 "$root/source/project/experiments/stream_quant_synthesis/precision_explore.py" \
 --checkpoint /public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/models/qwen25-3b-5defd279 --root "$root"
image=/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif
sha256sum "$image" > tools.sha256
exec srun --exact -n1 -c4 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
 --env SLURM_CPUS_PER_TASK=4 --env SLURM_JOB_ID="$SLURM_JOB_ID" "$image" \
 python3 -B "$root/source/project/experiments/stream_quant_synthesis/precision_rtl.py" --root "$root"
