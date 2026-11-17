#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
run=$(realpath "$1")
case "$run" in "$root"/cu/runs/U-*|"$root"/audit/U-antenna/candidate-*|"$root"/u-physical/candidate-*) ;; *) exit 2;; esac
out=$root/audit/full-$(basename "$run")
mkdir "$out"
res=$(find "$run/flow/results/nangate45" -mindepth 2 -maxdepth 2 -type d | head -1)
deck=/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc
printf '%s  %s\n' 4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147 "$deck" | sha256sum -c - > "$out/deck-identity.txt"
printf '%s\n' "$run" > "$out/source-run.txt"
sha256sum "$deck" "$res/6_final.gds" "$res/6_final.odb" "$res/6_final.sdc" "$res/6_final.spef" "$res/6_final.v" > "$out/inputs-before.sha256"
klayout -b -r "$deck" -rd "in_gds=$res/6_final.gds" -rd "report_file=$out/full.lyrdb" > "$out/full.log" 2>&1
sha256sum "$deck" "$res/6_final.gds" "$res/6_final.odb" "$res/6_final.sdc" "$res/6_final.spef" "$res/6_final.v" > "$out/inputs-after.sha256"
cmp "$out/inputs-before.sha256" "$out/inputs-after.sha256"
python3 - "$out" <<'PY'
from pathlib import Path
import sys,json,collections,hashlib,xml.etree.ElementTree as E
p=Path(sys.argv[1]);r=p/'full.lyrdb';items=E.parse(str(r)).findall('.//items/item');result=dict(full_foundry_deck_passed=not items,full_deck_items=len(items),categories=dict(collections.Counter(i.findtext('category') for i in items)),report_sha256=hashlib.sha256(r.read_bytes()).hexdigest(),deck_sha256='4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147',scope='Complete original unchanged FEOL/BEOL/grid/antenna deck on frozen actual merged GDS; requires independent STA/PG/functional release aggregation',accepted=False)
(p/'receipt.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2));sys.exit(0 if not items else 1)
PY
