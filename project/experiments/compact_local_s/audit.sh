#!/usr/bin/env bash
set -euo pipefail
task=$1
candidate=$2
out=$3
mode=${4:-audit}
extra=()
if [[ "$mode" == formal ]]; then
  extra=(--netlist "$5")
fi
cpus=$SLURM_CPUS_PER_TASK
export TMPDIR="$task/tmp-$SLURM_JOB_ID"
mkdir -p "$TMPDIR/cache"
exec srun --exact --ntasks=1 --cpus-per-task="$cpus" --cpu-bind=cores \
  /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv \
  --bind /public/home/yuzelu --pwd "$task/source" \
  --env "TMPDIR=$TMPDIR,XDG_CACHE_HOME=$TMPDIR/cache,PYTHONDONTWRITEBYTECODE=1,SLURM_JOB_ID=$SLURM_JOB_ID,OMP_NUM_THREADS=$cpus" \
  /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif \
  bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; exec python3 -B "$@"' bash \
  project/experiments/compact_local_s/"$mode".py --candidate "$candidate" --out "$out" \
  --bank-lib /public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-155/bank-views-011/generation/bank/s_sram_256x128_freepdk45_TT_1p1V_25C.lib "${extra[@]}"
