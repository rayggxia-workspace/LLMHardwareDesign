#!/bin/bash
#SBATCH -J yzl-C-generic-stage
#SBATCH -p c96,c64
#SBATCH -N1
#SBATCH -n1
#SBATCH -c8
#SBATCH -t 04:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-generic-stage-v2-%j.log
set -euo pipefail
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -e; source /OpenROAD-flow-scripts/env.sh; export PATH=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/eqy-install-v068/bin:$PATH; python3 /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/prepare-c-generic-stage-v2.py /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/C-v16-genericadder-cached; cd /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v16-genericadder-cached-generic-stage-v2-views; eqy -j8 -d proof-work proof.eqy'
