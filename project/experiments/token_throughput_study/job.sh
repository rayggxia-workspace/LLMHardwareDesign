#!/usr/bin/env bash
#SBATCH --job-name=mdt-tps-study
#SBATCH --partition=c64
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail
# c64 advertises RealMemory=1 MiB; memory is not schedulable on this cluster.
# Bound this analysis process tree to 12 GiB instead of requesting fictitious TRES.
ulimit -v 12582912
root=$SLURM_SUBMIT_DIR
cd "$root/source"
sha256sum -c "$root/source-files.sha256"
scontrol show job "$SLURM_JOB_ID" > "$root/allocation.txt"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 python3 -B project/experiments/token_throughput_study/check.py > "$root/check.log" 2>&1
exec srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 python3 -B project/experiments/token_throughput_study/analyse.py \
 --source /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-219-block-search/algorithm-fix-277-phased-tile-full \
 --probe /public/home/yuzelu/project-circuit/LLMHardwareDesign/side-token-probe-20261109-01 \
 --out "$root/results"
