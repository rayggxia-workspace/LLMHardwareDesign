#!/usr/bin/env bash
#SBATCH --job-name=yzl-dma-native
#SBATCH --partition=c64
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --nodes=1
#SBATCH --time=0
set -euo pipefail
root=$SLURM_SUBMIT_DIR
skids=${ISSUE250_DMA_SKIDS_PER_CHANNEL:-3}
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
echo "49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a  $image" | sha256sum -c
cd "$root/source"
sha256sum -c "$root/source.sha256" > "$root/source-check.log"
mkdir -p "$root/tmp"
for seed in 25021 25022 25023 25024 25025 25026; do
 srun --exclusive --exact -n1 -c10 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$root/source" \
 --env "TMPDIR=$root/tmp,PYTHONDONTWRITEBYTECODE=1" "$image" bash -c \
 'set -euo pipefail; for limit in 65535 3; do python3 project/experiments/w8a16_dma/check.py --source "$1/source" --out "$1/seed-$2-limit-$limit" --seed "$2" --serial-limit "$limit" --skids-per-channel "$3"; done' _ "$root" "$seed" "$skids" > "$root/seed-$seed.log" 2>&1 &
done
wait
for seed in 25021 25022 25023 25024 25025 25026; do
 test -s "$root/seed-$seed-limit-65535/result.json"
 test -s "$root/seed-$seed-limit-3/result.json"
done
