#!/bin/bash
#SBATCH --job-name=yzl-bv2-rgeomdiag
#SBATCH --partition=c96
#SBATCH --cpus-per-task=16
#SBATCH --time=24:00:00
set -euo pipefail
root=$1
out=$2
source=$3
candidate=$4
mode=$5
test "$SLURM_CPUS_PER_TASK" -eq 16
test ! -e "$out"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
test "$(sha256sum "$image" | cut -d' ' -f1)" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
srun --ntasks=1 --cpus-per-task=16 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public:/public --pwd "$root" "$image" \
 /usr/bin/time -v bash -c 'set -e; source /OpenROAD-flow-scripts/env.sh; python3 "$1/project/experiments/block_v2/r_geometry_diagnostic.py" --out "$2" --source "$3" --candidate "$4" --mode "$5"' bash "$root" "$out" "$source" "$candidate" "$mode"
