#!/bin/bash
#SBATCH -J yzl-C-notch
#SBATCH -p debug
#SBATCH -N1
#SBATCH -n1
#SBATCH -c8
#SBATCH -t 00:20:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v35-upper-patch-v2/upper-%j.log
set -euo pipefail
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; klayout -b -r /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v35-independent-v1/C-v35-unified-i8-h100-pnone/focused/upper-spacing-diagnostic-v2.lydrc -rd in_gds=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v35-upper-patch-v2/patched.gds -rd report_file=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-v35-upper-patch-v2/upper.lyrdb'
