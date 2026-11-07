#!/usr/bin/env bash
set -euo pipefail
out=$1
src=$2
candidate=$3
export SINGULARITYENV_SLURM_CPUS_PER_TASK=$SLURM_CPUS_PER_TASK
export SINGULARITYENV_OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
exec srun --exact --ntasks=1 --cpus-per-task="$SLURM_CPUS_PER_TASK" --cpu-bind=cores \
 /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
 --bind /public/home/yuzelu /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
 bash -c 'set -euo pipefail;source /OpenROAD-flow-scripts/env.sh;python3 -B "$1/project/experiments/mother_control_v1/gate.py" --candidate "$3" --out "$2" --upstream "$1/control180"' bash "$src" "$out" "$candidate"
