#!/bin/bash
#SBATCH --job-name=yzl-sc234-spwr
#SBATCH --partition=c64,c96,debug
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --time=00:30:00
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark/s-activity-*) ;; *) exit 2;; esac
[[ ${SLURM_NNODES:-0} = 1 && ${SLURM_NTASKS:-0} = 6 && ${SLURM_CPUS_PER_TASK:-0} = 10 ]] || exit 2
cd "$root"
sha256sum *.py *.cpp *.sv *.tsv *.sbatch >input.sha256
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$root" \
 --env OMP_NUM_THREADS=10,OPENBLAS_NUM_THREADS=10,MKL_NUM_THREADS=10,PYTHONDONTWRITEBYTECODE=1,SLURM_NTASKS=6,SLURM_CPUS_PER_TASK=10 \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c '
 set -euo pipefail
 source /OpenROAD-flow-scripts/env.sh
 python3 -u s_activity.py >calibration.log 2>&1
 sha256sum s-calibration.json base-*/receipt.json p-*/receipt.json >output.sha256
 '
