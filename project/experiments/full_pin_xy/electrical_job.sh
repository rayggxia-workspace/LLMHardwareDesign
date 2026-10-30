#!/bin/bash
#SBATCH --job-name=hpy-p126-elecobs
#SBATCH --partition=c96
#SBATCH --cpus-per-task=4
#SBATCH --time=0
#SBATCH --mem=0
set -euo pipefail
cd /public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027
export TMPDIR=$PWD/tmp PYTHONDONTWRITEBYTECODE=1
python3 -B "$PINXY_DRIVER_DIR/run_electrical_audit.py" "$@"
