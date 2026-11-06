#!/usr/bin/env bash
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
repo="$PWD"
case="${1:?route case directory}"
odb="${2:?routed OpenDB path}"
run="$repo/check-${SLURM_JOB_ID:?}"
mkdir "$run" "$run/tmp"
cat > "$run/export.tcl" <<TCL
read_db {$odb}
source {$repo/project/experiments/block_v1/odb_geometry.tcl}
bvgeom::export {$run/wire-rectangles.tsv}
TCL
envs="QT_QPA_PLATFORM=offscreen,TMPDIR=$run/tmp,QWEN_CHECK_CASE=$case,QWEN_CHECK_RUN=$run"
if [[ -n "${3:-}" ]]; then envs+=",QWEN_PROTECTED_GDS=$3"; fi
runtime=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv
    --bind /public/home/yuzelu --env "$envs"
    /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif)
"${runtime[@]}" bash -c '
    set -euo pipefail
    source /OpenROAD-flow-scripts/env.sh
    openroad -no_init -exit "$1"
    klayout -b -r "$2"
' _ "$run/export.tcl" "$repo/project/experiments/nine_block_route/check_switch_odb.py"
(cd "$run"; sha256sum independent-upper.json upper-only.gds wire-rectangles.tsv > SHA256SUMS)
