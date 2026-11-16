#!/usr/bin/env bash
set -euo pipefail
p=$(dirname "$(sacct -j 114252 -X -n -P -o WorkDir%500 | head -n 1)")
base=/public/home/yuzelu/PingyangHuang/hpy-pr271-top-hsVf4b/inputs
sw=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["views"]["SW.odb"]["path"])' "$p/../overlay-111993/base.json")
test -f "$sw"
mkdir -p tmp
sed 's/{metal7 metal8 metal9 metal10}/{metal7 metal8 metal9 metal10 via9}/g' "$p/export-pr271-metal.tcl" > export-sw-with-cuts.tcl
tool=/public/home/yuzelu/project-circuit/issue185-joint-packet-dma-bound-20261113-01/tool.sh
bash "$tool" env "AUDIT_ODB=$sw" "AUDIT_OUT=$PWD/native-sw.tsv" openroad -no_init -exit "$PWD/export-sw-with-cuts.tcl"
bash "$tool" bash -c 'f=/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef; test -f "$f"; sed -n "/^LAYER metal9$/,/^END metal9$/p; /^LAYER via9$/,/^END via9$/p; /^LAYER metal10$/,/^END metal10$/p" "$f"; grep -A14 -Ei "^VIA (via9|via_9)" "$f" | head -n 200' > lower-tech.lef.txt
sha256sum native-sw.tsv lower-tech.lef.txt "$base/placement.json" "$sw"
