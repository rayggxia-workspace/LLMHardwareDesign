#!/bin/bash
#SBATCH -J yzl-cached-eqy
#SBATCH -p c96,c64
#SBATCH -N1
#SBATCH -n1
#SBATCH -c8
#SBATCH -t 04:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/cached-eqy-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$root" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; export PATH="$1/eqy-install-v068/bin:$PATH"; cd "$1/eqy-tool-source/eqy-0.68/examples/simple"; eqy -j8 -d "$1/eqy-smoke-counter" counter.eqy; cd "$1"; eqy -j8 -d cached-eqy-v1 cached-rtl-map.eqy' _ "$root"
