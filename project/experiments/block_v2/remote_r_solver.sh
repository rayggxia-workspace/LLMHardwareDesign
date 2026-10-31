#!/usr/bin/env bash
#SBATCH --job-name=yzl-bv2-rcec
#SBATCH --partition=c96
#SBATCH --cpus-per-task=16
#SBATCH --time=01:00:00
set -euo pipefail
root=$1
out=$2
source=$3
test "$SLURM_CPUS_PER_TASK" -eq 16
test -f "$root/source-manifest.json"
test -f "$source/flow/objects/nangate45/bv1_block_v1_r/base/4_rsz_lec_test.yml"
mkdir -p "$out"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
read -r actual _ < <(sha256sum "$image")
test "$actual" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
srun --ntasks=1 --cpus-per-task=16 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$root" \
 --env OMP_NUM_THREADS=16 --env OPENBLAS_NUM_THREADS=1 "$image" \
 /usr/bin/time -v bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh
 exec python3 "$1/project/experiments/block_v2/probe_r_solver.py" --source "$3" --out "$2/solver"' \
 bash "$root" "$out" "$source" > "$out/solver-worker.log" 2>&1
