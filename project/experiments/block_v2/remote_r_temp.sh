#!/usr/bin/env bash
#SBATCH --job-name=yzl-bv2-rtemp
#SBATCH --partition=c96
#SBATCH --cpus-per-task=16
#SBATCH --time=24:00:00
set -euo pipefail
root=$1
out=$2
test "$SLURM_CPUS_PER_TASK" -eq 16
test -f "$root/source-manifest.json"
mkdir -p "$out"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
read -r actual _ < <(sha256sum "$image")
test "$actual" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
srun --ntasks=1 --cpus-per-task=16 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$root" \
 --env OMP_NUM_THREADS=16 --env OPENBLAS_NUM_THREADS=1 "$image" \
 /usr/bin/time -v bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh
 python3 "$1/project/experiments/block_v2/verify_r_temp.py" --out "$2/rtl/r"
 python3 "$1/project/experiments/block_v2/map.py" --model r --rtl-receipt "$2/rtl/r/receipt.json" --out "$2/mapping/block_v1_r"
 python3 "$1/project/experiments/block_v2/physical.py" --top block_v1_r --mapping "$2/mapping" --out "$2/pnr/r" --input-receivers --placement-mode geometric --fanout-mode partition --refine-partition-placement --placement-hold-margin 0.0' \
 bash "$root" "$out" > "$out/r-worker.log" 2>&1
