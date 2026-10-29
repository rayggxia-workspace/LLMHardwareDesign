#!/bin/bash
#SBATCH --job-name=hpy-p126-fairSources
#SBATCH --partition=c96
#SBATCH --cpus-per-task=1
#SBATCH --time=0
#SBATCH --mem=0
set -euo pipefail
cd /public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027
export PYTHONDONTWRITEBYTECODE=1
python3 -B "$PINXY_DRIVER_DIR/inventory_fair_boundary_sources.py" "$@"
