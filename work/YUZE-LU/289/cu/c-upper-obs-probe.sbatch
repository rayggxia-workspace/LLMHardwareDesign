#!/bin/bash
#SBATCH -J yzl-289-C-obs
#SBATCH -p debug,c96,c64
#SBATCH -N1
#SBATCH -n1
#SBATCH -c2
#SBATCH --time=00:05:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/c-upper-obs-%j.log
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/c-upper-obs-probe.tcl