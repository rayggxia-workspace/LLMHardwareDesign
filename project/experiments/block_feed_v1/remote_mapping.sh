#!/usr/bin/env bash
#SBATCH --job-name=yzl-mfeed
#SBATCH --partition=c96
#SBATCH --cpus-per-task=4
#SBATCH --mem=48G
#SBATCH --time=02:00:00
set -euo pipefail
source_root=$1
output_root=$2
test -n "${SLURM_JOB_ID:-}"
test "$SLURM_CPUS_PER_TASK" -ge 2
image=/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif
expected=49eae8b526c6eec806473b13db5d98f848424f38de9fa3430e8ce8e157144f3a
mkdir -p "$output_root"
sha256sum "$image" > "$output_root/image.sha256"
read -r actual _ < "$output_root/image.sha256"
test "$actual" = "$expected"
export PATH="/public/software/singularity-ce-4.3.4/bin:$PATH"
singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$source_root" \
 --env OMP_NUM_THREADS=1 --env OPENBLAS_NUM_THREADS=1 "$image" \
 bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; python3 "$1/project/experiments/block_feed_v1/inspect.py" --yosys "$(command -v yosys)" --abc "$(command -v yosys-abc)" --liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib --out "$2/mapping"' \
 bash "$source_root" "$output_root"
