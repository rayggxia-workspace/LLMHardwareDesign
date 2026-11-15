#!/usr/bin/env bash
set -euo pipefail
p=$(dirname "$(sacct -j 114252 -X -n -P -o WorkDir%500 | head -n 1)")
sw=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["views"]["SW.odb"]["path"])' "$p/../overlay-111993/base.json")
test -f "$sw"
mkdir -p tmp
sed 's/{metal7 metal8 metal9 metal10}/{metal7 metal8 metal9 metal10 via7 via8 via9}/g' "$p/export-pr271-metal.tcl" > export-sw-cuts.tcl
tool=/public/home/yuzelu/project-circuit/issue185-joint-packet-dma-bound-20261113-01/tool.sh
bash "$tool" env "AUDIT_ODB=$sw" "AUDIT_OUT=$PWD/native-sw-full.tsv" openroad -no_init -exit "$PWD/export-sw-cuts.tcl"
bash "$tool" bash -c 'f=/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef; sed -n "/^LAYER metal7$/,/^END metal7$/p; /^LAYER metal8$/,/^END metal8$/p; /^LAYER metal9$/,/^END metal9$/p; /^LAYER metal10$/,/^END metal10$/p; /^LAYER via7$/,/^END via7$/p; /^LAYER via8$/,/^END via8$/p; /^LAYER via9$/,/^END via9$/p" "$f"; grep -A10 -Ei "^VIA via[789]_0 " "$f"' > lower-tech-full.txt
sha256sum native-sw-full.tsv lower-tech-full.txt "$sw"
