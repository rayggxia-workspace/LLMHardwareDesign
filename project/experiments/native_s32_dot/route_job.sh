#!/usr/bin/env bash
#SBATCH --job-name=yzl-dot32-route
#SBATCH --partition=c64
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=10
#SBATCH --time=0
set -euo pipefail
root=$SLURM_SUBMIT_DIR
cd "$root"
sha256sum -c source.sha256 > source-check.log
scontrol show job "$SLURM_JOB_ID" > allocation.txt
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
echo "49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a  $image" | sha256sum -c > tools.log
mkdir "$root/tool-tmp"
exec srun --exact -n1 -c10 --cpu-bind=cores bash -c '
 set -euo pipefail
 allowed=$(python3 -c '\''import os;print(",".join(str(x) for x in sorted(os.sched_getaffinity(0))))'\'')
 exec /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu \
  --env "SLURM_JOB_ID=$SLURM_JOB_ID,TMPDIR=$1/tool-tmp,PYTHONDONTWRITEBYTECODE=1,OMP_NUM_THREADS=10" \
  "$2" taskset -c "$allowed" bash -c '\''set -euo pipefail;source /OpenROAD-flow-scripts/env.sh;exec python3 "$@"'\'' bash \
  "$1/source/project/experiments/native_s32_dot/route_native.py" --mapping "$NATIVE32_MAPPING" \
  --out "$1/route" --rows "$NATIVE32_ROWS" --side "$NATIVE32_SIDE" --density "$NATIVE32_DENSITY"
' bash "$root" "$image"
