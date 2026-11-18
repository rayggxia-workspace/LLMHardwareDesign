#!/bin/bash
#SBATCH --job-name=yzl-289-U-diag
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --time=00:30:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/U-diag-%j.log
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
run=$root/audit/U-antenna/candidate-guard-ant-v1
out=$root/audit/U-guard-ant-v1-diagnose
mkdir "$out"
export U_RUN=$run
export U_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$run/config.mk" | tail -1)
export U_RESULTS=$run/flow/results/nangate45/u-overlay-current/base
/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu --pwd "$out" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/u-diagnose-v2.tcl'
