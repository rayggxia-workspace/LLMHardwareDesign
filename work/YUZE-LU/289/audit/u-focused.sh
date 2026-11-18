#!/bin/bash
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
run=$(realpath "$1")
case "$run" in "$root"/cu/runs/U-*|"$root"/audit/U-antenna/candidate-*|"$root"/u-physical/candidate-*|"$root"/audit/U-v15-pg-diagnostic) ;; *) exit 2;; esac
out=$root/audit/focused-$(basename "$run")
mkdir "$out"
res=$(find "$run/flow/results/nangate45" -mindepth 2 -maxdepth 2 -type d | head -1)
test -s "$res/6_final.gds"
cp "$root/u-physical/upper-spacing-diagnostic-v2.lydrc" "$root/audit/U-antenna/antenna-only-v2.lydrc" "$out/"
printf '%s\n' "$run" > "$out/source-run.txt"
sha256sum "$res/6_final.gds" "$out/"*.lydrc > "$out/inputs-before.sha256"
klayout -b -r "$out/upper-spacing-diagnostic-v2.lydrc" -rd "in_gds=$res/6_final.gds" -rd "report_file=$out/upper.lyrdb" > "$out/upper.log" 2>&1
klayout -b -r "$out/antenna-only-v2.lydrc" -rd "in_gds=$res/6_final.gds" -rd "report_file=$out/antenna.lyrdb" > "$out/antenna.log" 2>&1
sha256sum "$res/6_final.gds" "$out/"*.lydrc > "$out/inputs-after.sha256"
cmp "$out/inputs-before.sha256" "$out/inputs-after.sha256"
python3 - "$out" <<'PY'
import sys,json,collections,xml.etree.ElementTree as E
from pathlib import Path
p=Path(sys.argv[1]);r=dict(accepted=False,scope='Focused diagnostics only; complete unchanged foundry deck, fresh STA, PG and functional gates remain mandatory')
for name in ('upper','antenna'):
 items=E.parse(str(p/(name+'.lyrdb'))).findall('.//items/item')
 r[name]=dict(count=len(items),categories=dict(collections.Counter(i.findtext('category') for i in items)),markers=[dict(category=i.findtext('category'),cell=i.findtext('cell'),values=[v.text for v in i.findall('values/value')]) for i in items])
r['diagnostics_clear']=all(r[k]['count']==0 for k in ('upper','antenna'));(p/'receipt.json').write_text(json.dumps(r,indent=2));print(json.dumps({k:({'count':v['count'],'categories':v['categories']} if isinstance(v,dict) else v) for k,v in r.items()},indent=2))
PY
