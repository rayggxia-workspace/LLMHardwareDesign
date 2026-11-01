#!/bin/bash
#SBATCH --job-name=yzl-rarch157-native
#SBATCH --partition=c96
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=96
#SBATCH --mem=0
#SBATCH --time=24:00:00
set -euo pipefail
cd "$1"
sha256sum --check FILES.sha256 > source-check.log
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
test "$(sha256sum "$image" | cut -d' ' -f1)" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$1" "$image" bash -c 'source /OpenROAD-flow-scripts/env.sh; python3 project/experiments/r_architecture/micro.py --only c_wide_native --out "$1/unit"; python3 project/experiments/r_architecture/cosim_sweep.py --native-only --out "$1/results"' bash "$1"
