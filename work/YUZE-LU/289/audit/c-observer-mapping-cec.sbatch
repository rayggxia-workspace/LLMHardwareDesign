#!/bin/bash
#SBATCH -J yzl-C-parent-cec
#SBATCH -p c96,c64
#SBATCH -N1
#SBATCH -n1
#SBATCH -c8
#SBATCH -t 04:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-observer-mapping-cec-%j.log
set -euo pipefail
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; python3 /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/run_observer_cec.py /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v16-synth-replay'
