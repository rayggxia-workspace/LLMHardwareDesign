#!/bin/bash
#SBATCH --job-name=mdt-rprobe200
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --time=0
#SBATCH --output=probe-slurm-%j.log
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
srun --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; python3 -B probe_power_reader.py'
