#!/usr/bin/env bash
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
repo="$PWD"
inputs=$(realpath -e "${1:?compute macro and research stack inputs}")
plan=$(realpath -e "${2:?verified side-channel plan}")
native=$(realpath -e "${3:?physically routed transport}")
run="$repo/channel-verify-${SLURM_JOB_ID:?}"
src="$repo/project/experiments/nine_block_route"
gds="$native/flow/results/nangate45/qwen_nine_transport/base/6_final.gds"

python3 -B "$src/bind_switch.py" "$inputs" "$native/switch.lef" "$gds" "$run" nine channel \
    --layout-plan "$plan/layout-plan.json"
python3 -B "$src/channel_plan.py" check-bound "$plan" "$run"
python3 -B "$src/validate_escape.py" "$run/route.json"
python3 -B "$src/export_escape.py" "$run/route.json"
mkdir "$run/tmp" "$run/odb-check"

cat > "$run/import.tcl" <<TCL
read_lef {$inputs/research12.tech.lef}
read_lef {$inputs/P.lef}
read_lef {$inputs/U.lef}
read_lef {$inputs/C.lef}
read_lef {$inputs/F.lef}
read_lef {$inputs/J.lef}
read_lef {$native/switch.lef}
read_def {$run/route.def}
write_db {$run/routed.odb}
source {$repo/project/experiments/block_v1/odb_geometry.tcl}
bvgeom::export {$run/odb-check/wire-rectangles.tsv}
TCL

runtime=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv
    --bind /public/home/yuzelu
    --env "QT_QPA_PLATFORM=offscreen,TMPDIR=$run/tmp,COUPON_AUDIT=$run,QWEN_CHECK_CASE=$run,QWEN_CHECK_RUN=$run/odb-check"
    /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif)
"${runtime[@]}" bash -c '
    set -euo pipefail
    source /OpenROAD-flow-scripts/env.sh
    klayout -b -r "$1/check_gds.py"
    openroad -no_init -exit "$2/import.tcl"
    klayout -b -r "$1/check_switch_odb.py"
' _ "$src" "$run"
(cd "$run"; sha256sum case-binding.json inputs.json route.def routed.odb route.json route-audit.json \
    upper-only.gds klayout-receipt.json odb-check/independent-upper.json > SHA256SUMS)
