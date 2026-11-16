#!/usr/bin/env bash
#SBATCH --job-name=yzl-e-route
#SBATCH --partition=c64
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --nodes=1
#SBATCH --time=0
set -euo pipefail
root=$SLURM_SUBMIT_DIR
map_from=$1
cd "$root/source"
sha256sum -c "$root/source.sha256" > "$root/source-check.log"
scontrol show job "$SLURM_JOB_ID" > "$root/allocation.txt"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
echo "49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a  $image" | sha256sum -c
pids=()
for side in 232 234; do
 tmp="$root/tmp-$side"
 mkdir -p "$tmp/cache"
 srun --exact -n1 -c10 --cpu-bind=cores \
  /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
  --env "TMPDIR=$tmp,XDG_CACHE_HOME=$tmp/cache,PYTHONDONTWRITEBYTECODE=1,SLURM_JOB_ID=$SLURM_JOB_ID,OMP_NUM_THREADS=10,OPENBLAS_NUM_THREADS=1" \
  "$image" bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; exec python3 "$@"' bash \
  "$root/source/project/experiments/w8a16_physical/g_route.py" --top e_s32_ap64 --mapping "$map_from/map" \
  --out "$root/route-$side" --side "$side" --density .78 --margin 14 \
  > "$root/route-$side.log" 2>&1 &
 pids+=("$!")
done
failed=0
for pid in "${pids[@]}"; do wait "$pid" || failed=1; done
exit "$failed"
