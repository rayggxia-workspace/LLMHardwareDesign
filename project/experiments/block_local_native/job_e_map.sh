#!/usr/bin/env bash
#SBATCH --job-name=yzl-e-map
#SBATCH --partition=c64
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --nodes=1
#SBATCH --time=0
set -euo pipefail
root=$SLURM_SUBMIT_DIR
rtl_run=$1
shift
leaf=e_s32_native
if [[ ${1:-} == --ap64 ]]; then leaf=e_s32_ap64; fi
cd "$root/source"
sha256sum -c "$root/source.sha256" > "$root/source-check.log"
scontrol show job "$SLURM_JOB_ID" > "$root/allocation.txt"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
echo "49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a  $image" | sha256sum -c
pids=()
mkdir -p "$root/map"
for top in "$leaf" e_s128_frontend; do
 tmp="$root/tmp-$top"
 mkdir -p "$tmp/cache"
 srun --exact -n1 -c10 --cpu-bind=cores \
  /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
  --env "TMPDIR=$tmp,XDG_CACHE_HOME=$tmp/cache,PYTHONDONTWRITEBYTECODE=1,SLURM_JOB_ID=$SLURM_JOB_ID,OMP_NUM_THREADS=10,OPENBLAS_NUM_THREADS=1" \
  "$image" bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; exec python3 "$@"' bash \
  "$root/source/project/experiments/w8a16_physical/e_map.py" --rtl-run "$rtl_run" --out "$root/map/$top" --top "$top" "$@" \
  > "$root/map-$top.log" 2>&1 &
 pids+=("$!")
done
failed=0
for pid in "${pids[@]}"; do wait "$pid" || failed=1; done
exit "$failed"
