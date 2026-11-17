#!/bin/bash
#SBATCH -J yzl-eqy-build
#SBATCH -p debug
#SBATCH -N1
#SBATCH -n1
#SBATCH -c8
#SBATCH -t 00:20:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/eqy-build-%j.log
set -euo pipefail
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/eqy-tool-source/eqy-0.68 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; make -j3 PREFIX=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/eqy-install-v068 install'
