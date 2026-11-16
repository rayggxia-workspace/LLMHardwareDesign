#!/bin/bash
#SBATCH --job-name=yl-250LCjoin
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --time=00:20:00
#SBATCH --output=slurm-%j.out
set -euo pipefail
CONTROL_ROOT=${CONTROL_SOURCE_DIR:?actual archived source root}
export ROOT_NATIVE_DIR=${ROOT_NATIVE_DIR:?actual pinned root native sources}
CONTROL_SOURCE_DIR="${CONTROL_ROOT}/project/experiments/shared_x_control" \
  bash "${CONTROL_ROOT}/project/experiments/shared_x_control/lc_native.sbatch"
CONTROL_SOURCE_DIR="${CONTROL_ROOT}" \
  bash "${CONTROL_ROOT}/project/experiments/shared_x_control/mc_lc_native.sbatch"
