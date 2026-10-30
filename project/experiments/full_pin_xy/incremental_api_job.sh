#!/bin/bash
#SBATCH --job-name=hpy-p126-routeAPI
#SBATCH --partition=c96
#SBATCH --cpus-per-task=1
#SBATCH --time=0
#SBATCH --mem=0
set -euo pipefail
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
cd /public/home/yuzelu/PingyangHuang/issue-126/full-pin-20261027
test ! -e tool_api/incremental-r01
mkdir -p tool_api/incremental-r01
singularity exec --cleanenv --home "$PWD/home" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif /OpenROAD-flow-scripts/tools/install/OpenROAD/bin/openroad -threads 1 -no_init -exit "$PINXY_DRIVER_DIR/incremental_api.tcl" > tool_api/incremental-r01/native.log 2>&1
