#!/bin/bash
#SBATCH --partition=c96
#SBATCH --job-name=yzl-bv2-rfullcec
#SBATCH --cpus-per-task=48
#SBATCH --time=04:00:00
set -euo pipefail
source_dir=$1
out=$2
native_source=$3
exec /public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public:/public /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif /bin/bash -c '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
export OMP_NUM_THREADS=16
python3 "$1/project/experiments/block_v2/probe_r_full_state.py" --source "$3" --out "$2" --workers 3
' bash "$source_dir" "$out" "$native_source"
