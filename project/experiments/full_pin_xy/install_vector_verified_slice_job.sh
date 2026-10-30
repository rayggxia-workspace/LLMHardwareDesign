#!/bin/bash
#SBATCH --job-name=hpy126-vslice
#SBATCH --partition=c96
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=0
#SBATCH --time=0
set -euo pipefail
export PATH=/public/software/singularity-ce-4.3.4/bin:$PATH
cd /public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027
export TMPDIR=$PWD/tmp SINGULARITY_CACHEDIR=$PWD/cache SINGULARITY_TMPDIR=$PWD/tmp PYTHONDONTWRITEBYTECODE=1
python3 "$PINXY_DRIVER_DIR/install_vector_verified_slice.py" "$1"
