#!/bin/bash
#SBATCH -J yzl-289-C-fastHold
#SBATCH -p debug
#SBATCH -N1
#SBATCH -n1
#SBATCH -c8
#SBATCH --time=00:30:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/c-fast-hold-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu
out=$root/diagnostics/C-fast-hold-probe-v1
mkdir -p "$out";cd "$out"
libs=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$root/runs/C-v27-joint-e20-h30/config.mk" | tail -1)
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env "OMP_NUM_THREADS=8,CU_LIBS=$libs" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "$root/c-fast-hold-probe-v1.tcl" > openroad.log 2>&1
