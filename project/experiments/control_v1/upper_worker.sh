#!/usr/bin/env bash
#SBATCH --job-name=yzl-ctl162-upper
#SBATCH --partition=c96
#SBATCH --cpus-per-task=16
#SBATCH --time=06:00:00
set -euo pipefail
root=$1
c=$2
queue=$3
out=$4
seed=${5:-0}
test -n "${SLURM_JOB_ID:-}"
python3 "$root/project/experiments/control_v1/bundle_source.py" --verify "$root"
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
read -r actual _ < <(sha256sum "$image")
test "$actual" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
srun --exclusive --ntasks=1 --cpus-per-task=16 --cpu-bind=cores singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$root" \
 --env OMP_NUM_THREADS=16 --env QT_QPA_PLATFORM=offscreen --env SLURM_JOB_ID="$SLURM_JOB_ID" "$image" \
 /usr/bin/time -v bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; exec python3 "$@"' bash \
 "$root/project/experiments/control_v1/upper_link.py" --c "$c" --queue "$queue" --out "$out" --seed "$seed"
