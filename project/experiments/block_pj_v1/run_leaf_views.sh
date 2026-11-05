#!/usr/bin/env bash
#SBATCH --job-name=yzl-pjviews
#SBATCH --partition=c96
#SBATCH --nodes=1
#SBATCH --ntasks=6
#SBATCH --cpus-per-task=4
#SBATCH --time=02:00:00
set -euo pipefail
repo=$1
root=$2
container=/public/software/singularity-ce-4.3.4/bin/singularity
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
pids=()
mkdir -p "$root/views"
for leaf in M G E T p4 n4; do
    srun --exclusive -n1 -c4 --cpu-bind=cores "$container" exec --cleanenv \
        --bind /public/home/yuzelu "$image" /usr/bin/time -v bash -c '
        set -euo pipefail
        source /OpenROAD-flow-scripts/env.sh
        python3 "$1/project/experiments/block_pj_v1/export_leaf.py" "$1" "$2" "$3"
    ' bash "$repo" "$root" "$leaf" > "$root/views/$leaf-worker.log" 2>&1 &
    pids+=("$!")
done
status=0
for pid in "${pids[@]}"; do wait "$pid" || status=1; done
exit "$status"
