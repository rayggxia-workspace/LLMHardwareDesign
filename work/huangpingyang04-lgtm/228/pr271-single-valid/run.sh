#!/usr/bin/env bash
set -euo pipefail
root=$(pwd -P)
tmp=$(mktemp -d "$root/tmp-XXXXXX")
export TMPDIR="$tmp" XDG_CACHE_HOME="$tmp" PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
export PYTHONPATH="$root/project/experiments/upper_router:$root/project/experiments/block_synthesis"
input="$root/inputs/top-1834"
libs="$root/cells.lib"
mode=${1:-original}
budget=${2:-500000}
mkdir "$mode"
cd "$mode"
sha256sum "$input/algorithm2-input.json" "$root/inputs/placement.json" "$libs" "$root/single_valid.py" > inputs.sha256
runtime=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv
  --bind /public/home/yuzelu --env "TMPDIR=$TMPDIR,XDG_CACHE_HOME=$XDG_CACHE_HOME"
  /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif)
run_sta() {
  local case=$1
  (cd "$case"
   "${runtime[@]}" bash -c 'source /OpenROAD-flow-scripts/env.sh; exec openroad -no_init -threads 2 -exit sta.tcl' > sta.log 2>&1)
}
python3 -B "$root/single_valid.py" direct "$input" "$libs" "$budget" "$mode"
run_sta direct
python3 -B "$root/single_valid.py" buffer "$input" "$libs" "$budget" "$mode"
run_sta buffered
python3 -B "$root/single_valid.py" summary "$input" "$libs"
sha256sum summary.json direct/sta.log buffered/sta.log > outputs.sha256
