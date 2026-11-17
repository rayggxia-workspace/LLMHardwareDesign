#!/bin/bash
#SBATCH --job-name=yzl-ab-native
#SBATCH --partition=debug,c64,c96
#SBATCH --cpus-per-task=1
#SBATCH --time=00:10:00
set -euo pipefail
cd /public/home/yuzelu/project-circuit/issue287-route-ab-all-20261117
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit g_native.tcl
