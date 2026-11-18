#!/bin/bash
#SBATCH -J yzl-289-Cselect
#SBATCH -p debug
#SBATCH -N1
#SBATCH -n1
#SBATCH -c8
#SBATCH --time=00:10:00
#SBATCH -o /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/c-margin-select-%j.log
set -euo pipefail
r=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif python3 "$r/cu/c-margin-plans-select-v1.py" "$r/cu/diagnostics/C-actual-seven-size-v4" "$r/cu/diagnostics/C-actual-seven-size-v4/selectedplans"
