#!/bin/bash
#SBATCH --job-name=mdt-rpower200
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --time=0
#SBATCH --output=slurm-%j.log
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
sha256sum -c postprocess-inputs.sha256
test -f gate-replay-receipt.json
if test -f window-0-active.log; then cp -p window-0-active.log initial-window-0-active.log; fi
srun --cpu-bind=cores /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; python3 -B calibrate_final.py'
