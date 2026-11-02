#!/bin/bash
#SBATCH --job-name=yzl-r157-synccost
#SBATCH --partition=c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=16
#SBATCH --mem=0
#SBATCH --exclusive
#SBATCH --time=UNLIMITED
set -euo pipefail
cd "$1"
sha256sum --check FILES.sha256 > source-check.log
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
test "$(sha256sum "$image" | cut -d' ' -f1)" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$1" "$image" bash -c 'source /OpenROAD-flow-scripts/env.sh; exec python3 project/experiments/r_architecture/sync_systemc.py'
