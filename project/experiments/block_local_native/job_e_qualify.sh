#!/usr/bin/env bash
#SBATCH --job-name=yzl-e-qual
#SBATCH --partition=c64
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --nodes=1
#SBATCH --time=0
set -euo pipefail
root=$SLURM_SUBMIT_DIR
source_run=$1
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
 "$image" bash -c '
   set -euo pipefail
   source /OpenROAD-flow-scripts/env.sh
   unset VERILATOR_ROOT
   tools=$1/source/project/experiments/w8a16_physical
   candidate=$2/route-$3
   out=$1/candidate-$3
   python3 -B "$tools/g_audit.py" --top e_s32_ap64 --source "$candidate" --out "$out" > "$1/audit-$3.log" 2>&1
   python3 -B "$tools/e_function.py" --source "$out/sealed" --out "$out/final-function" > "$1/function-$3.log" 2>&1
   python3 -B "$tools/g_formal.py" --top e_s32_ap64 --source "$out/sealed" --function "$out/final-function" --out "$out/formal" > "$1/formal-$3.log" 2>&1
 ' bash "$root" "$source_run" "$side" > "$root/candidate-$side.log" 2>&1 &
 pids+=("$!")
done
failed=0
for pid in "${pids[@]}"; do wait "$pid" || failed=1; done
exit "$failed"
