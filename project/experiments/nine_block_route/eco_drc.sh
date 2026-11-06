#!/usr/bin/env bash
set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
base="$PWD"
i="${1:?}"; n="${2:?}"; kind="${3:?}"
candidate="$base/eco-$i-$n"
resume="${4:-}"; if [[ -n "$resume" ]]; then resume="$(realpath "$resume")"; fi
stream_only="${5:-}"
run="$base/native-${SLURM_JOB_ID:?}-$kind"
mkdir "$run"
ln -s "$candidate/eco-routed.def" "$run/"
cd "$run"
proj="$(realpath ../../..)"
deck="$proj/issue-188-ucf16/accepted-ucf16-01/C16/FreePDK45.lydrc"
eng="$proj/issue-188-ucf16/well-engine-0309/release"
runtime=(/public/software/singularity-ce-4.3.4/bin/singularity exec --cleanenv --bind /public/home/yuzelu --env "SLURM_JOB_ID=$SLURM_JOB_ID" /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif)
"${runtime[@]}" bash -c '
set -euo pipefail
source /OpenROAD-flow-scripts/env.sh
export QT_QPA_PLATFORM=offscreen
flow=/OpenROAD-flow-scripts/flow
p=$flow/platforms/nangate45
bank="$2/issue-155/bank-views-011/generation/bank"
views="$2/issue-187-p16-j16/005-leaf-views"
lefs=("$p/lef/NangateOpenCellLibrary.tech.lef" "$p/lef/NangateOpenCellLibrary.macro.mod.lef")
gds=("$p/gds/NangateOpenCellLibrary.gds")
if [[ $1 == P ]]; then
  for m in p4 M G; do
    lefs+=("$views/views/$m/leaf.lef")
    gds+=("$views/inputs/$m/6_final.gds")
  done
else
  provision="$2/local-s-sram-qualification-20261105-01/attempt02/n4/physical"
  lefs+=("$provision/bank-with-routing-landings.lef")
  gds+=("$provision/bank-stream.gds")
fi
if [[ -n "$5" ]]; then
  ln -s "$5" eco-raw.gds
else
python3 "$flow/util/generate_klayout_tech.py" --template "$p/FreePDK45.lyt" --output "$PWD/eco.lyt" --lef-files "${lefs[@]}"
# The GDS writer uses the outer technology DBU. Match the LEF/DEF
# reader DBU to preserve the physical die, pin and routing coordinates.
sed -i "0,/<dbu>0.0005<\/dbu>/s//<dbu>0.0001<\/dbu>/" eco.lyt
klayout -zz -rd "design_name=block_${1,,}16" -rd "in_def=$PWD/eco-routed.def" -rd "in_files=${gds[*]}" \
  -rd seal_file= -rd "out_file=$PWD/eco-raw.gds" -rd "tech_file=$PWD/eco.lyt" -rd layer_map= -r "$flow/util/def2stream.py" > stream.log 2>&1
fi
klayout -b -r "$2/issue-188-ucf16/audit-13/coalesce_wells.py" \
  -rd "SOURCE=$PWD/eco-raw.gds" -rd "OUTPUT=$PWD/eco.gds" -rd "RECEIPT=$PWD/well-equivalence.json" > stream-wells.log 2>&1
if [[ "$6" == stream-only ]]; then exit 0; fi
export LD_LIBRARY_PATH="$4/usr/lib/klayout:${LD_LIBRARY_PATH:-}"
"$4/usr/bin/klayout" -v
"$4/usr/bin/klayout" -b -r "$3" -rd "in_gds=$PWD/eco.gds" -rd "report_file=$PWD/eco-native.lyrdb" > native-full.log 2>&1
' _ "$kind" "$proj" "$deck" "$eng" "$resume" "$stream_only"
if [[ "$stream_only" == stream-only ]]; then exit 0; fi
python3 - <<'PY'
import xml.etree.ElementTree as ET
n=len(ET.parse("eco-native.lyrdb").findall(".//items/item"))
print("Full native markers:",n)
raise SystemExit(bool(n))
PY
