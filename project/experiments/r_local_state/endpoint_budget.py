"""Measure maximum-delay headroom at every actual extracted hold-failing endpoint."""
from pathlib import Path
import argparse, hashlib, json, subprocess
p=argparse.ArgumentParser();p.add_argument('--diagnosis',type=Path,required=True);a=p.parse_args()
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
diagnosis=json.loads((a.diagnosis/'receipt.json').read_text());assert diagnosis['passed']
inputs=diagnosis['inputs'];assert all(sha(Path(f))==h for f,h in inputs.items())
rows=[r.split('\t')for r in(a.diagnosis/'failing-paths.tsv').read_text().splitlines()]
assert rows and all(r[0]=='min'and r[2].endswith('/D')and float(r[3])<0 for r in rows)
ends={}
for r in rows:ends[r[2]]=min(ends.get(r[2],0),float(r[3]))
assert len(ends)<=1000
files=[next(Path(f)for f in inputs if f.endswith('.'+ext))for ext in ['odb','sdc','spef']]
O=Path.cwd()/'endpoint-budget';O.mkdir(exist_ok=False)
t='''set_thread_count 16
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db {%s}
read_sdc {%s}
read_spef {%s}
set_propagated_clock [all_clocks]
sta::find_timing
set f [open endpoint-budgets.tsv w]
'''%tuple(str(f)for f in files)
for name,slack in sorted(ends.items()):
 assert '{'not in name and '}'not in name and '\n'not in name
 t+='set name {'+name+'}\n'
 t+='''set pins [get_pins [list $name]]
if {[llength $pins]!=1} {error "Missing actual endpoint $name"}
set paths [find_timing_paths -to $pins -path_delay max -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained max path to $name"}
puts $f "$name\t'''+str(slack)+'''\t[get_property [lindex $paths 0] slack]"
'''
t+='close $f\n'
(O/'probe.tcl').write_text(t)
with(O/'probe.log').open('w')as log:r=subprocess.run(['openroad','-exit','probe.tcl'],cwd=O,stdout=log,stderr=subprocess.STDOUT)
assert all(sha(Path(f))==h for f,h in inputs.items())
out=[]
if r.returncode==0:
 for row in(O/'endpoint-budgets.tsv').read_text().splitlines():
  name,hold,setup=row.split('\t');out.append(dict(endpoint=name,hold_ns=float(hold),setup_ns=float(setup)))
 assert len(out)==len(ends)and {x['endpoint']for x in out}==set(ends)
receipt=dict(passed=r.returncode==0,inputs=inputs,diagnosis=str(a.diagnosis),diagnosis_receipt_sha256=sha(a.diagnosis/'receipt.json'),failing_paths_sha256=sha(a.diagnosis/'failing-paths.tsv'),rows=out,probe_sha256=sha(O/'probe.tcl'),scope='Read-only exact final SPEF endpoint headroom; no new qualification or acceptance change.')
(O/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
raise SystemExit(r.returncode)
