#!/usr/bin/env bash
#SBATCH --job-name=yzl-pjgates
#SBATCH --partition=c96
#SBATCH --nodes=1
#SBATCH --ntasks=8
#SBATCH --cpus-per-task=12
#SBATCH --time=12:00:00
set -euo pipefail
repo=$1
leaves=$2
physical=$3
root=$4
container=/public/software/singularity-ce-4.3.4/bin/singularity
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
mkdir -p "$root"
awk '/^MemAvailable:/ {print; if ($2 < 192 * 1024 * 1024) exit 1}' /proc/meminfo > "$root/memory-admission.txt"
pids=()
for block in P J; do
    for gate in electrical physical drc function; do
        srun --exclusive -n1 -c12 --cpu-bind=cores "$container" exec --cleanenv \
            --bind /public/home/yuzelu --env OMP_NUM_THREADS=12 --env OPENBLAS_NUM_THREADS=1 \
            "$image" /usr/bin/time -v bash -c '
            set -euo pipefail
            source /OpenROAD-flow-scripts/env.sh
            python3 "$1/project/experiments/block_pj_v1/gate.py" "$@"
        ' bash "$repo" "$leaves" "$physical" "$root" "$block" "$gate" > "$root/$block-$gate-worker.log" 2>&1 &
        pids+=("$!")
    done
done
status=0
for pid in "${pids[@]}"; do wait "$pid" || status=1; done
exit "$status"
