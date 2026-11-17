#!/bin/bash
#SBATCH --job-name=yzl-ab-resistors
#SBATCH --partition=debug,c64,c96
#SBATCH --cpus-per-task=2
#SBATCH --time=00:20:00
set -euo pipefail
cd /public/home/yuzelu/project-circuit/issue287-distributed-20261117
for scheme in A B; do
 (cd rcx-$scheme; /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit run.tcl > run.log 2>&1) &
done
wait
