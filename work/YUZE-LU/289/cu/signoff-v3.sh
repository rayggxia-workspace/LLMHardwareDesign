#!/bin/bash
# Run inside allocated ORFS container. Full rules; reports remain fail-closed.
set -euo pipefail
run=$(realpath "$1")
case "$run" in /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/runs/*) ;; *) exit 2;; esac
export CU_RESULTS=$(find "$run/flow/results/nangate45" -mindepth 2 -maxdepth 2 -type d | head -1)
export CU_SIGNOFF=$run/signoff
mkdir -p "$CU_SIGNOFF"
export CU_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$run/config.mk" | tail -1)
source /OpenROAD-flow-scripts/env.sh
openroad -no_init -exit /public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/cu/signoff-v3.tcl > "$CU_SIGNOFF/signoff.log" 2>&1
deck=/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc
sha256sum "$deck" "$CU_RESULTS/6_final.gds" "$CU_RESULTS/6_final.sdc" "$CU_RESULTS/6_final.spef" > "$CU_SIGNOFF/sha256-before.txt"
klayout -b -r "$deck" -rd "in_gds=$CU_RESULTS/6_final.gds" -rd "report_file=$CU_SIGNOFF/full.lyrdb" > "$CU_SIGNOFF/klayout.log" 2>&1
sha256sum "$deck" "$CU_RESULTS/6_final.gds" "$CU_RESULTS/6_final.sdc" "$CU_RESULTS/6_final.spef" > "$CU_SIGNOFF/sha256-after.txt"
cmp "$CU_SIGNOFF/sha256-before.txt" "$CU_SIGNOFF/sha256-after.txt"
python3 - "$CU_SIGNOFF" <<'PY'
import json,sys,pathlib,xml.etree.ElementTree as ET
p=pathlib.Path(sys.argv[1])
counts={a:int(b) for a,b in (line.split() for line in (p/'counts.tsv').read_text().splitlines())}
counts['full_drc']=len(ET.parse(p/'full.lyrdb').findall('.//items/item'))
result={'counts':counts,'timing_electrical_drc_pass':all(v==0 for v in counts.values()),'functional_equivalence':'pending separate LEC','accepted':False}
(p/'report.json').write_text(json.dumps(result,indent=2)+'\n')
if not result['timing_electrical_drc_pass']:sys.exit(1)
PY
