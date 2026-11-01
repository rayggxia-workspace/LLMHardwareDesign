#!/bin/bash
#SBATCH --job-name=yzl-rarch157
#SBATCH --partition=c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=96
#SBATCH --mem=0
#SBATCH --time=12:00:00
set -euo pipefail
root=$1
cd "$root"
sha256sum --check FILES.sha256 > source-check.log
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
test "$(sha256sum "$image" | cut -d' ' -f1)" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
test "$(awk '/MemAvailable/ {print $2}' /proc/meminfo)" -ge 350000000
export OMP_NUM_THREADS=16 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$root" "$image" bash -c 'source /OpenROAD-flow-scripts/env.sh; export OMP_NUM_THREADS=16 PYTHONDONTWRITEBYTECODE=1; exec python3 project/experiments/r_architecture/worker.py --out "$1"' bash "$root/results"
