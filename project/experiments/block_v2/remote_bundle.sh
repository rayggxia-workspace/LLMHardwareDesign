#!/usr/bin/env bash
#SBATCH --job-name=yzl-bv2-pack
#SBATCH --partition=c96
#SBATCH --cpus-per-task=16
#SBATCH --time=02:00:00
set -euo pipefail
root=$1
base=$2
out=$3
models=${4:-e g}
test "$SLURM_CPUS_PER_TASK" -eq 16
test -f "$root/source-manifest.json"
mkdir -p "$out"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
read -r actual _ < <(sha256sum "$image")
test "$actual" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
srun --ntasks=1 --cpus-per-task=16 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$root" "$image" \
 bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh
 for model in $4; do
  case "$model" in
   e|g) gates=010;;
   n) gates=022;;
   m) gates=018;;
   r) gates=019;;
   *) echo "Unsupported leaf: $model" >&2; exit 1;;
  esac
  python3 "$1/project/experiments/block_v2/bundle.py" --delivery "$2/outputs/$gates/deliver-$model" --out "$3/bundle-$model"
 done' bash "$root" "$base" "$out" "$models"
