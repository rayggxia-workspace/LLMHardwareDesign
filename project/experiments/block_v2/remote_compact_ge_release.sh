#!/usr/bin/env bash
#SBATCH --job-name=yzl-ge-release
#SBATCH --partition=c64
#SBATCH --cpus-per-task=10
#SBATCH --array=0-1%2
#SBATCH --time=01:00:00
set -euo pipefail
root=$1
out=$2
shift 2
case "${SLURM_ARRAY_TASK_ID:?}" in
  0) model=g ;;
  1) model=e_compact ;;
  *) exit 2 ;;
esac
selected=
for final in "$@"; do
    if [[ -f "$final/$model/formal/formal.json" ]]; then
        selected=$final/$model
        break
    fi
done
test -n "$selected"
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
read -r digest _ < <(sha256sum "$image")
test "$digest" = 49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
srun --exclusive --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
 singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$out" \
 --env OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK" --env OPENBLAS_NUM_THREADS=1 "$image" \
 bash -c '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
export PYTHONDONTWRITEBYTECODE=1
python3 "$1/project/experiments/block_v2/compact_release.py" "$2" "$3/$4"
cd "$3"
tar -czf "$4.tar.gz" "$4"
sha256sum "$4.tar.gz" > "$4.tar.gz.sha256"
' bash "$root" "$selected" "$out" "$model"
