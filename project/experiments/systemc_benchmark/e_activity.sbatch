#!/bin/bash
#SBATCH --job-name=yzl-sc234-epwr
#SBATCH --partition=debug
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --time=00:30:00
set -euo pipefail
root=$(realpath "$1")
case "$root" in /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-234-systemc-benchmark/e-activity-*) ;; *) exit 2;; esac
cd "$root"
sha256sum *.py *.cpp *.sv *.tsv *.sbatch >input.sha256
[[ "$SLURM_NTASKS" = 6 && "$SLURM_CPUS_PER_TASK" = 10 ]] || exit 2
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$root" \
 --env OMP_NUM_THREADS=10,OPENBLAS_NUM_THREADS=10,MKL_NUM_THREADS=10,PYTHONDONTWRITEBYTECODE=1,SLURM_NTASKS=6,SLURM_CPUS_PER_TASK=10 \
 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c '
 set -euo pipefail
 source /OpenROAD-flow-scripts/env.sh
 python3 -u e_activity.py >calibration.log 2>&1
 sha256sum e-calibration.json cohort-*/receipt.json >output.sha256
 '
