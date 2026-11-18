#!/bin/bash
#SBATCH --job-name=yzl-C-xnor-probe
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=00:30:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-xnor-probe-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
python3 "$root/audit/c-xnor-isolation-prepare.py"
export CU_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$root/cu/runs/C-v27-joint-e20-h30/config.mk" | tail -1)
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env "CU_LIBS=$CU_LIBS" --pwd "$root/audit/C-xnor-isolation-conditional-v1" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -no_init -exit "$root/audit/c-xnor-isolation.tcl"
