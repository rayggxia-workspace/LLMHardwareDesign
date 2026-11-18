#!/bin/bash
#SBATCH --job-name=yzl-289-C-antdry
#SBATCH --partition=c96,c64
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=01:00:00
#SBATCH --output=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/C-antdry-%j.log
set -euo pipefail
r=/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117
export C_ANT_ECO_PACKAGE=$r/audit/C-antenna-v27-r2
export C_ANT_ECO_SOURCE_ODB=$r/cu/runs/C-v27-joint-e20-h30/flow/results/nangate45/c-overlay-current/base/6_final.odb
out=$C_ANT_ECO_PACKAGE/dry-edit-$SLURM_JOB_ID
mkdir "$out"
sha256sum "$C_ANT_ECO_SOURCE_ODB" "$C_ANT_ECO_PACKAGE/"*.tcl "$C_ANT_ECO_PACKAGE/"*.json "$C_ANT_ECO_PACKAGE/selected-outputs.txt" > "$out/inputs-before.sha256"
/public/software/singularity-ce-4.3.4/bin/singularity exec --bind /public/home/yuzelu --pwd "$out" --env OMP_NUM_THREADS=8,OPENBLAS_NUM_THREADS=1 /public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif bash -c 'set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; openroad -no_init -exit "$C_ANT_ECO_PACKAGE/dry-edit.tcl" > edit.log 2>&1; openroad -no_init -exit "$C_ANT_ECO_PACKAGE/readback.tcl" > readback.log 2>&1'
sha256sum "$C_ANT_ECO_SOURCE_ODB" "$C_ANT_ECO_PACKAGE/"*.tcl "$C_ANT_ECO_PACKAGE/"*.json "$C_ANT_ECO_PACKAGE/selected-outputs.txt" > "$out/inputs-after.sha256"
cmp "$out/inputs-before.sha256" "$out/inputs-after.sha256"
python3 - "$out" <<'PY'
from pathlib import Path
import sys,json,csv,hashlib,collections
p=Path(sys.argv[1]);rows=list(csv.DictReader((p/'antenna-insertions.tsv').open(),delimiter='\t'));assert len(rows)==17 and len({r['net'] for r in rows})==17 and len({r['diode'] for r in rows})==17
readback=(p/'diode-readback.tsv').read_text().splitlines();assert len(readback)==17
assert (p/'original-before.tsv').read_bytes()==(p/'original-after.tsv').read_bytes()==(p/'original-readback.tsv').read_bytes()
assert (p/'antenna-interface-before.tsv').read_bytes()==(p/'antenna-interface-after.tsv').read_bytes()==(p/'interface-readback.tsv').read_bytes()
assert len((p/'selected-drivers.tsv').read_text().splitlines())==153
files=[p/x for x in ('candidate.odb','candidate.def','candidate.v','antenna-insertions.tsv','diode-readback.tsv','selected-drivers.tsv','original-before.tsv','original-after.tsv','original-readback.tsv','antenna-interface-before.tsv','antenna-interface-after.tsv','interface-readback.tsv','inputs-before.sha256','inputs-after.sha256')]
def sha(q):
 h=hashlib.sha256()
 with q.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
r=dict(passed=True,accepted=False,scope='Allocated copy-only OpenDB structural dry edit and fresh DB readback. Not legalized/routed/electrical/PG-physical/antenna/full-deck qualified.',diodes_added=17,one_per_expected_input_net=True,original_instances_placement_master_terminal_nets_exact=True,interface_die_macro_geometry_exact=True,selected_output_drivers_unchanged=153,anchor_modes=dict(collections.Counter(x['anchor_mode'] for x in rows)),placement_modes=dict(collections.Counter(x['placement_mode'] for x in rows)),source_sha256={str(q):sha(q) for q in files})
(p/'receipt.json').write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items() if k!='source_sha256'},indent=2))
PY
