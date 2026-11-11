#!/usr/bin/env bash
#SBATCH --job-name=mdt-pdma
#SBATCH --partition=c64,c96
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail
root=$SLURM_SUBMIT_DIR
cd "$root/source"
sha256sum -c "$root/source-files.sha256"
scontrol show job "$SLURM_JOB_ID" > "$root/allocation.txt"
image=/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif
prefix=/public/home/yuzelu/opt/systemc-3.0.2-issue219
sha256sum "$image" "$prefix/lib/libsystemc.so" > "$root/tools.sha256"
export PYTHONDONTWRITEBYTECODE=1 OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
exec srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
 --env SLURM_CPUS_PER_TASK="$SLURM_CPUS_PER_TASK" "$image" \
 python3 -B project/experiments/p_dma_study/run.py --inputs "$root/inputs" --out "$root/results" --workers "$SLURM_CPUS_PER_TASK" --phase adaptive
