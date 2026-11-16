#!/usr/bin/env bash
#SBATCH --job-name=yzl-xprotocol
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --time=00:10:00
#SBATCH --output=batch-%j.log
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
sha256sum -c source.sha256 > source-check.log
scontrol show job "$SLURM_JOB_ID" > allocation.txt
srun --exact -n6 -c10 --cpu-bind=cores --output=protocol-%t.json bash -c 'exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env SLURM_PROCID="$SLURM_PROCID" /public/home/yuzelu/opt/eda/containers/orfs-26Q1-repacked.sif python3 -B shared_x_payload_check.py'
