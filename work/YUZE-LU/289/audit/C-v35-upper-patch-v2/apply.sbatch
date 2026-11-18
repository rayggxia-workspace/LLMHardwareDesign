#!/bin/bash
#SBATCH -J yzl-C-notch
#SBATCH -p debug
#SBATCH -N1
#SBATCH -n1
#SBATCH -c8
#SBATCH -t 00:20:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v35-upper-patch-v2/apply-%j.log
set -euo pipefail
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; openroad -exit /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v35-upper-patch-v2/apply.tcl'
