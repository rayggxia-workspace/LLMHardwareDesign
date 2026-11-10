#!/usr/bin/env bash
#SBATCH --job-name=yl-sq-close-be
#SBATCH --partition=c64,c96
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=0
#SBATCH --output=closure-backend-slurm-%j.log
set -euo pipefail
root=$SLURM_SUBMIT_DIR
cd "$root/source"
sha256sum -c "$root/source-files.sha256" > "$root/source-check.log"
cd "$root"
scontrol show job "$SLURM_JOB_ID" > allocation.txt
image=/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif
sha256sum "$image" /public/home/yuzelu/opt/systemc-3.0.2-issue219/lib/libsystemc.so > tools.sha256
exec srun --exact -n1 -c4 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
 --env SLURM_CPUS_PER_TASK=4 --env SLURM_JOB_ID="$SLURM_JOB_ID" "$image" \
 python3 -B "$root/source/project/experiments/stream_quant_synthesis/closure_backend.py" --root "$root" --stage timing
