#!/usr/bin/env bash
#SBATCH --job-name=yzl-e-access
#SBATCH --partition=c64
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --nodes=1
#SBATCH --time=0
set -euo pipefail
root=$SLURM_SUBMIT_DIR
candidate=$1/candidate-234
cd "$root/source"
sha256sum -c "$root/source.sha256" > "$root/source-check.log"
scontrol show job "$SLURM_JOB_ID" > "$root/allocation.txt"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
echo "49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a  $image" | sha256sum -c
tmp="$root/tmp"
mkdir -p "$tmp/cache" "$root/tasks"
srun --exact -n1 -c10 --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
 --env "TMPDIR=$tmp,XDG_CACHE_HOME=$tmp/cache,PYTHONDONTWRITEBYTECODE=1,SLURM_JOB_ID=$SLURM_JOB_ID,OMP_NUM_THREADS=10,OPENBLAS_NUM_THREADS=1" \
 "$image" bash -c '
   set -euo pipefail
   source /OpenROAD-flow-scripts/env.sh
   tools=$1/source/project/experiments/w8a16_physical
   python3 -B "$tools/g_deliver.py" --top e_s32_ap64 --source "$2/sealed" --audit "$2" \
      --function "$2/final-function" --formal "$2/formal" --out "$1/delivery" > "$1/delivery.log" 2>&1
   python3 -B "$tools/g_access.py" --top e_s32_ap64 --source "$2/sealed" --delivery "$1/delivery" \
      --out "$1/tasks/e-access" > "$1/access.log" 2>&1
 ' bash "$root" "$candidate"
