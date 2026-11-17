#!/bin/bash
#SBATCH --job-name=yzl-ab-verify
#SBATCH --partition=debug,c64,c96
#SBATCH --cpus-per-task=1
#SBATCH --time=00:10:00
set -euo pipefail
cd /public/home/yuzelu/project-circuit/issue287-route-ab-all-20261117
python3 summarize_all.py
python3 validate_all.py
python3 make_manifest.py
