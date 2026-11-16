#!/usr/bin/env bash
set -euo pipefail
root=$(pwd -P)
variant=$1
mode=$2
phase=$3
weight=$4
out="$root/$variant/${mode}-${phase}-$SLURM_JOB_ID"
export TMPDIR="$root/$variant/tmp" XDG_CACHE_HOME="$root/$variant/tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
export PYTHONPATH="$root/project/experiments/upper_router:$root/project/experiments/block_synthesis"
if [[ $phase == ablation ]]; then
  python3 -B "$root/analysis/ablation.py" "$root/inputs/$variant" "$root/$variant/$mode" "$out" --weight "$weight"
else
  python3 -B "$root/analysis/timing.py" "$out" --study "$root/$variant/$mode" --liberty "$root/cells.lib"
  for case in "$out"/net-*; do
    (cd "$case"
     /public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --pwd "$case" --env "TMPDIR=$TMPDIR,XDG_CACHE_HOME=$XDG_CACHE_HOME" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'source /OpenROAD-flow-scripts/env.sh; exec openroad -no_init -threads 2 -exit run.tcl' > sta.log 2>&1)
  done
  python3 -B "$root/analysis/timing.py" "$out"
fi
sha256sum "$out"/*json
