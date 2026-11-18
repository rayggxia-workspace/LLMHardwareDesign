#!/bin/bash
#SBATCH --job-name=yzl-289-C-rcxverify
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=01:00:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-rcxverify-%j.log
set -euo pipefail
r=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
run=$(realpath "$1")
case "$run" in "$r"/cu/runs/C-*|"$r"/audit/C-*) ;; *) exit 2;; esac
out=$r/audit/C-final-v1/rcx-$(basename "$run")
mkdir "$out"
cp "$r/audit/C-final-v1/"{extract-consistency.tcl,geometry-all.tcl,def-material.py} "$out/"
export C_FINAL_RES=$(find "$run/flow/results/nangate45" -mindepth 2 -maxdepth 2 -type d | head -1)
export C_LIBS=$(sed -n 's/^export ADDITIONAL_LIBS = //p' "$run/config.mk" | tail -1)
export C_CANON_BASE=$out
export C_CANON_OUT=$out/material-audit
sha256sum "$C_FINAL_RES/6_final.odb" "$C_FINAL_RES/6_final.sdc" $C_LIBS "$out/"*.tcl "$out/def-material.py" > "$out/inputs-before.sha256"
/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu --pwd "$out" --env OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; sha256sum /OpenROAD-flow-scripts/flow/platforms/nangate45/rcx_patterns.rules > rcx-rules.sha256; openroad -no_init -exit extract-consistency.tcl > extraction.log 2>&1; klayout -b -r def-material.py > material.log 2>&1'
sha256sum "$C_FINAL_RES/6_final.odb" "$C_FINAL_RES/6_final.sdc" $C_LIBS "$out/"*.tcl "$out/def-material.py" > "$out/inputs-after.sha256"
cmp "$out/inputs-before.sha256" "$out/inputs-after.sha256"
cmp "$out/before-geometry.tsv" "$out/after-geometry.tsv"
cmp "$out/before-master-obs.tsv" "$out/after-master-obs.tsv"
python3 - "$out" <<'PY'
from pathlib import Path
import sys,json,hashlib
p=Path(sys.argv[1]);g=json.loads((p/'material-audit/receipt.json').read_text());assert g['passed'],g['geometry_differences'];pg=[s.split('\t') for s in (p/'post-rcx-pg.tsv').read_text().splitlines()];assert sorted(pg)==[['VDD','0','1'],['VSS','0','1']],pg
files=[p/x for x in ('before.def','after.def','isolated.spef','before.odb','after.odb','post-rcx-pg.tsv','inputs-before.sha256','inputs-after.sha256','rcx-rules.sha256','material-audit/receipt.json')]
r=dict(passed=True,scope='Isolated same-source RCX geometry/PG consistency only; full GDS/STA/formal acceptance separate',all_signal_material_exact=True,signal_nets=g['nets_checked'],macro_pins_obstructions_preserved=True,uncached_post_rcx_pg=pg,source_sha256={str(q):hashlib.sha256(q.read_bytes()).hexdigest() for q in files});(p/'receipt.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
PY
