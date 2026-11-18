#!/bin/bash
set -euo pipefail
seed=$1
case "$seed" in 0|1|2|3|4|5) ;; *) exit 2;; esac
r=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
pkg=$r/audit/C40-clock-graft-fast-v1
run=$r/cu/runs/C-v40-final-size-seed${seed}
binding=$r/audit/C-v40-independent-v1/C-v40-final-size-seed${seed}/frozen-source.json
python3 "$r/audit/C-v40-independent-v1/verify-binding.py" "$binding"
out=$pkg/seed${seed}
mkdir "$out"
cp "$pkg/"*.tcl "$pkg/"*.py "$pkg/clock-reference.json" "$out/"
cd "$out"
source /OpenROAD-flow-scripts/env.sh
export GRAFT_TARGET=$run/flow/results/nangate45/c-overlay-current/base/6_final.odb
export C_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$run/config.mk" | tail -1)
export C_FINAL_RES=$out/results U_RESULTS=$out/results U_LIBS=$C_LIBS
mkdir results source-meta target-meta rcx
python3 - "$run" "$binding" "$pkg/run.sh" <<'PYS'
import json,sys,hashlib,os
from pathlib import Path
run,binding,runner=map(Path,sys.argv[1:]);p=Path('.');ref=json.loads((p/'clock-reference.json').read_text());assert hashlib.sha256(Path(ref['path']).read_bytes()).hexdigest()==ref['sha256']
res=run/'flow/results/nangate45/c-overlay-current/base';files=[Path(ref['path']),res/'6_final.odb',res/'6_final.sdc',run/'config.mk',binding,runner,p/'clock-reference.json']+[Path(x) for x in os.environ['C_LIBS'].split()]+list(p.glob('*.py'))+list(p.glob('*.tcl'))+[Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules'),Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')]
(p/'inputs-before.sha256').write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+str(f.resolve())+'\n' for f in files))
PYS
export CLOCK_ODB=$r/audit/C-clock-layer-v7/m9/results/6_final.odb CLOCK_META=$out/source-meta
openroad -no_init -exit snapshot.tcl >source-snapshot.log 2>&1
export CLOCK_ODB=$GRAFT_TARGET CLOCK_META=$out/target-meta
openroad -no_init -exit snapshot.tcl >target-snapshot.log 2>&1
python3 generate.py source-meta target-meta generated >generate.log 2>&1
openroad -no_init -exit apply.tcl >apply.log 2>&1
klayout -b -r check-graft.py >structure.log 2>&1
cp "$run/flow/results/nangate45/c-overlay-current/base/6_final.sdc" results/6_final.sdc
cp extract-consistency.tcl geometry-all.tcl def-material.py rcx/
cd rcx
openroad -no_init -exit extract-consistency.tcl >extraction.log 2>&1
python3 - <<'PYS'
from pathlib import Path
assert sorted(Path('post-rcx-pg.tsv').read_text().splitlines())==['VDD\t0\t1','VSS\t0\t1']
PYS
cmp before-geometry.tsv after-geometry.tsv
cmp before-master-obs.tsv after-master-obs.tsv
cp isolated.spef "$out/results/6_final.spef.pending"
mv "$out/results/6_final.spef.pending" "$out/results/6_final.spef"
cd "$out"
rc=0;openroad -no_init -exit fresh.tcl >fresh.log 2>&1 || rc=$?
printf 'fresh_exit=%s\nbackend_accepted=false\nfull_rcx_material_and_native_gds_pending=true\n' "$rc" >status.txt
sha256sum -c inputs-before.sha256 >inputs-after-check.txt
python3 "$r/audit/C-v40-independent-v1/verify-binding.py" "$binding" >data-source-after.log
sha256sum results/6_final.{odb,def,sdc,v,spef} structural-receipt.json rcx/{before.def,after.def,isolated.spef,post-rcx-pg.tsv} fresh-counts.tsv fresh-setup.rpt fresh-hold.rpt fresh-pg-after-spef.tsv >outputs.sha256
printf 'complete_fast_diagnostic=true\nbackend_accepted=false\n' >READY-DIAGNOSTIC.txt
