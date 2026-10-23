#!/bin/bash
#SBATCH --job-name=lrz-i61-phi-get
#SBATCH --partition=c96
#SBATCH --cpus-per-task=2
#SBATCH --time=02:00:00
set -euo pipefail
root=/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023
export TMPDIR="$root/tmp" PYTHONDONTWRITEBYTECODE=1
cd "$root"
/public/home/yuzelu/RuizhiLiang/issue53-cpu-pilot-20261023/venv/bin/python -B phase2/source/download.py \
 --metadata phase2/phi-metadata.json --out models/phi4mini-cfbefacb
