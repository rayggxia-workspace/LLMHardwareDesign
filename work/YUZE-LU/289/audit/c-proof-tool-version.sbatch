#!/bin/bash
#SBATCH -J yzl-C-proof-tool-version
#SBATCH -p c96,c64
#SBATCH -N1
#SBATCH -n1
#SBATCH -c8
#SBATCH -t 04:00:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-proof-tool-version-%j.log
set -euo pipefail
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; yosys -V; yosys-abc -c version; sha256sum /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys /OpenROAD-flow-scripts/tools/install/yosys/bin/yosys-abc /OpenROAD-flow-scripts/tools/install/kepler-formal/bin/kepler-formal /OpenROAD-flow-scripts/tools/install/yosys/share/yosys/simcells.v'
