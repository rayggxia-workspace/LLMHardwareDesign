#!/bin/bash
#SBATCH --job-name=zny-head-read
#SBATCH --partition=c64,c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:45:00
#SBATCH --output=slurm-%j.out
set -euo pipefail
cd "$SLURM_SUBMIT_DIR"
export HEAD_READ_PIPELINE=1
exec bash run_native_head.sbatch baseline "$1"
