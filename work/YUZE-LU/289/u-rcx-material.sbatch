#!/bin/bash
#SBATCH --job-name=yzl-289-rcxgds
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=02:00:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/u-rcx-material-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
work=$root/u-physical/rcx-material-$SLURM_JOB_ID
seed=$root/audit/U-v15-pg-diagnostic
mkdir "$work"
cp "$seed/config.mk" "$work/"
for kind in results logs reports objects; do
 mkdir -p "$work/flow/$kind/nangate45/u-overlay-current/base"
done
res=$work/flow/results/nangate45/u-overlay-current/base
cp "$1" "$res/6_final.def"
export SINGULARITYENV_GDS_COMPARE_A="$seed/flow/results/nangate45/u-overlay-current/base/6_final.gds"
export SINGULARITYENV_GDS_COMPARE_B="$res/6_final.gds"
export SINGULARITYENV_GDS_COMPARE_OUT="$work/material.json"
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$work" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
make -C /OpenROAD-flow-scripts/flow DESIGN_CONFIG="$PWD/config.mk" WORK_HOME="$PWD/flow" NUM_CORES=8 do-gds > gds.log 2>&1
klayout -b -r /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/u-gds-material-compare.py > material.log 2>&1
'
