#!/usr/bin/env bash
#SBATCH --job-name=mdt-pool-port
#SBATCH --partition=c64,c96
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=02:00:00
#SBATCH --output=slurm-%j.log
set -euo pipefail
root=$SLURM_SUBMIT_DIR
cd "$root/source"
sha256sum -c "$root/source-files.sha256"
cd "$root"
sha256sum -c input-files.sha256
scontrol show job "$SLURM_JOB_ID" > allocation.txt
image=/public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif
prefix=/public/home/yuzelu/opt/systemc-3.0.2-issue219
sha256sum "$image" "$prefix/lib/libsystemc.so" > tools.sha256
exec srun --exact -n1 -c "$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
 --env SLURM_CPUS_PER_TASK="$SLURM_CPUS_PER_TASK" --env SLURM_JOB_ID="$SLURM_JOB_ID" "$image" \
 python3 -B "$root/source/project/experiments/shared32_native/legacy_port_probe/run.py" --root "$root"
