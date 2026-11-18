#!/bin/bash
# Run only on allocated compute resources; diagnostic, never acceptance.
set -euo pipefail
root=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
run=$(realpath "$1")
case "$run" in "$root"/cu/runs/C-*) ;; *) exit 2;; esac
out=$root/c-physical/focused-$(basename "$run")
mkdir -p "$root/c-physical"
mkdir "$out"
res=$run/flow/results/nangate45/c-overlay-current/base
test -s "$res/6_final.gds"
cp "$root/u-physical/upper-spacing-diagnostic-v2.lydrc" "$root/audit/U-antenna/antenna-only-v2.lydrc" "$out/"
printf '%s\n' "$run" > "$out/source-run.txt"
sha256sum "$res/6_final.gds" "$res/6_final.odb" "$res/6_final.def" "$out/"*.lydrc > "$out/inputs-before.sha256"
klayout -b -r "$out/upper-spacing-diagnostic-v2.lydrc" -rd "in_gds=$res/6_final.gds" -rd "report_file=$out/upper.lyrdb" > "$out/upper.log" 2>&1
klayout -b -r "$out/antenna-only-v2.lydrc" -rd "in_gds=$res/6_final.gds" -rd "report_file=$out/antenna.lyrdb" > "$out/antenna.log" 2>&1
sha256sum "$res/6_final.gds" "$res/6_final.odb" "$res/6_final.def" "$out/"*.lydrc > "$out/inputs-after.sha256"
cmp "$out/inputs-before.sha256" "$out/inputs-after.sha256"
python3 - "$out" <<'PY'
import sys,json,collections,hashlib,xml.etree.ElementTree as E
from pathlib import Path
p=Path(sys.argv[1]);r=dict(accepted=False,scope='C diagnostic only; full unchanged deck, fresh STA/electrical, PG, function, drive and geometry gates remain required')
for name in ('upper','antenna'):
 report=p/(name+'.lyrdb');items=E.parse(report).findall('.//items/item')
 r[name]=dict(count=len(items),report_sha256=hashlib.sha256(report.read_bytes()).hexdigest(),categories=dict(collections.Counter(i.findtext('category') for i in items)),markers=[dict(category=i.findtext('category'),cell=i.findtext('cell'),values=[v.text for v in i.findall('values/value')]) for i in items])
r['diagnostics_clear']=all(r[k]['count']==0 for k in ('upper','antenna'))
(p/'receipt.json').write_text(json.dumps(r,indent=2))
print(json.dumps({k:({'count':v['count'],'categories':v['categories']} if isinstance(v,dict) else v) for k,v in r.items()},indent=2))
PY
