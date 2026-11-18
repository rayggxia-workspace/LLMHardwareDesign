#!/bin/bash
#SBATCH --job-name=yzl-289-C-nativeaudit
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=01:00:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-nativeaudit-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
export C_NATIVE_SPEC=$(realpath "$1")
test -f "$C_NATIVE_SPEC"
/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu --env C_NATIVE_SPEC="$C_NATIVE_SPEC",OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; klayout -b -r "$1"' _ "$root/audit/C-final-native-v1/check.py"
