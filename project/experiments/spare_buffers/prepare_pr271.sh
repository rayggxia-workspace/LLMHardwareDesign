#!/usr/bin/env bash
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
export QT_QPA_PLATFORM=offscreen
script=$(cd "$(dirname "$0")" && pwd -P)
placement=$(realpath -e "$1")
archive=$(realpath -e "$2")
p=/OpenROAD-flow-scripts/flow/platforms/nangate45
util=/OpenROAD-flow-scripts/flow/util
python3 -B - "$placement" "$archive" > sources.tsv <<'PY'
import json
import sys

placement = json.load(open(sys.argv[1]))
archive = json.load(open(sys.argv[2]))
boxes = placement["boxes_dbu"]
if set(boxes) != {a["id"] for a in archive["assemblies"]}:
    raise ValueError("Placement and archive have different block sets")
for a in archive["assemblies"]:
    key = a["views"].get("gds") or a["views"]["odb"]
    view = archive["views"][key]
    print(a["id"], key, view["path"], view["sha256"], sep="\t")
PY
sed "s@\./NangateOpenCellLibrary.mod.lef@$p/lef/NangateOpenCellLibrary.tech.lef</lef-files><lef-files>$p/lef/NangateOpenCellLibrary.macro.mod.lef@" \
    "$p/FreePDK45.lyt" > leaf.lyt
printf 'block\tpath\tsource_view\tsource_sha256\torigin_x_dbu\torigin_y_dbu\n' > views.tsv
declare -A seen
convert_view() (
    local block=$1 kind=$2 input=$3 hash=$4
    mkdir "$block"
    cd "$block"
    export LEAF_ODB="$input"
    openroad -no_init -exit "$script/export_leaf.tcl" > export.log 2>&1
    read -r marker design dbu x0 y0 x1 y1 < <(grep '^LEAF ' export.log)
    test "$dbu" = 2000
    local gds="$p/gds/NangateOpenCellLibrary.gds"
    if [[ "$kind" == U.Gather.odb ]]; then
        local donor donor_hash
        read -r donor donor_hash < <(python3 -B -c 'import json,sys; v=json.load(open(sys.argv[1]))["views"]["U.gds"]; print(v["path"], v["sha256"])' "$archive")
        printf '%s  %s\n' "$donor_hash" "$donor" | sha256sum -c
        klayout -b -r "$script/extract_masters.py" -rd "input_gds=$donor" -rd output_gds=macros.gds \
            -rd masters=n_s32_softmax_s128,local_s_base,block_v2_e_compact,s_sram_256x128_freepdk45 > macros.log 2>&1
        gds="$gds $PWD/macros.gds"
        sha256sum macros.gds
    fi
    klayout -b -r "$util/def2stream.py" -rd tech_file=../leaf.lyt -rd layer_map= \
        -rd in_def=leaf.def -rd design_name="$design" -rd in_files="$gds" \
        -rd seal_file= -rd out_file=leaf.gds > stream.log 2>&1
    printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$block" "$PWD/leaf.gds" "$kind" "$hash" "$x0" "$y0" >> ../views.tsv
    sha256sum leaf.gds leaf.def
)
while IFS=$'\t' read -r block kind input hash; do
    if [[ ! -v seen[$kind] ]]; then
        printf '%s  %s\n' "$hash" "$input" | sha256sum -c
        seen[$kind]=1
    fi
    if [[ $kind == *.gds ]]; then
        printf '%s\t%s\t%s\t%s\t0\t0\n' "$block" "$input" "$kind" "$hash" >> views.tsv
        continue
    fi
    convert_view "$block" "$kind" "$input" "$hash"
done < sources.tsv
