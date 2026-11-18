#!/bin/bash
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:15:00
#SBATCH --job-name=yzl-neighbor-netcheck
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C40-neighbor-rip-plan-v1/job-%j.log
set -euo pipefail
cd /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C40-neighbor-rip-plan-v1
sha256sum all-nets.txt validate.tcl validate.sbatch /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v40-final-sizes/regenerated-ap.odb >validation-inputs-before.sha256
/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit validate.tcl' >validation.log 2>&1
sha256sum -c validation-inputs-before.sha256 >validation-inputs-after-check.txt
