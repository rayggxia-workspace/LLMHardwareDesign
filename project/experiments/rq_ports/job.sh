#!/bin/bash
#SBATCH --job-name=lrz-rqports
#SBATCH --partition=debug
#SBATCH --cpus-per-task=8
#SBATCH --time=00:20:00
#SBATCH --output=slurm-%j.out
set -euo pipefail
case "$PWD" in /public/home/yuzelu/RuizhiLiang/issue51-rq-ports-20261023/*) ;; *) exit 2 ;; esac
mkdir -p tmp
export TMPDIR="$PWD/tmp"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
python3 source/server.py --root "$PWD" --workers 8
