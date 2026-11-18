#!/bin/bash
#SBATCH --job-name=yzl-C-metalguard
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=01:00:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-metalguard-%j.log
set -euo pipefail
out=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v27-s-m9-guard-v2
/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu --pwd "$out" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -e; source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit probe.tcl > probe.log 2>&1'
