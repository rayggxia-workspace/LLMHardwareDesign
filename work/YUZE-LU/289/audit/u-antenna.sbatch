#!/bin/bash
#SBATCH --job-name=yzl-289-U-antenna
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=03:00:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/U-antenna-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -e; python3 "$1/audit/u-antenna-deck.py"; klayout -b -r "$1/audit/U-antenna/antenna-only-v2.lydrc" -rd in_gds="$1/cu/runs/U-v13-electrical-f50-x4/flow/results/nangate45/u-overlay-current/base/6_final.gds" -rd report_file="$1/audit/U-antenna/f50x4-antenna.lyrdb"' _ "$root"
