#!/bin/bash
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=01:00:00
#SBATCH --job-name=yzl-C35-pg-material
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v35-pg-boundary-v3/job-%j.log
set -euo pipefail
cd /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v35-pg-boundary-v3
sha256sum *.tsv check.py run.sbatch /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v35-unified-i8-h100-pnone/flow/results/nangate45/c-overlay-current/base/6_final.gds >inputs-before.sha256
export PG_GDS=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v35-unified-i8-h100-pnone/flow/results/nangate45/c-overlay-current/base/6_final.gds
/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; klayout -b -r check.py' >check.log 2>&1
sha256sum -c inputs-before.sha256 >inputs-after-check.txt
