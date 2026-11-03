"""Read-only paired-path evidence for measured topology/routing changes."""
from pathlib import Path
import argparse,hashlib,json,subprocess
p=argparse.ArgumentParser();p.add_argument('--physical',type=Path,required=True);p.add_argument('--diagnosis',type=Path,required=True);p.add_argument('--capacity',type=int,choices=[1024],required=True);a=p.parse_args()
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
dr=json.loads((a.diagnosis/'receipt.json').read_text());assert dr['passed']
assert all(sha(Path(f))==h for f,h in dr['inputs'].items())
rows=[r.split('\t')for r in(a.diagnosis/'failing-paths.tsv').read_text().splitlines()]
assert rows and len(rows)<=1000 and all(r[0]=='min'and r[1].endswith('/Q')and r[2].endswith('/D')and float(r[3])<0 for r in rows)
pairs=sorted({(r[1],r[2])for r in rows});assert len(pairs)==len(rows)
R=a.physical/'flow/results/nangate45'/('r166_'+str(a.capacity))/'base'
files=[R/('6_final.'+e)for e in ['odb','sdc','spef']];inputs={str(f):sha(f)for f in files}
O=Path.cwd()/'selected-paths';O.mkdir(exist_ok=False)
t='''set_thread_count 16
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db {%s}
read_sdc {%s}
read_spef {%s}
set_propagated_clock [all_clocks]
sta::find_timing
set f [open selected-min.tsv w]
set r [open selected-min.rpt w];close $r
'''%tuple(str(f)for f in files)
for start,end in pairs:
 assert all(not any(c in name for c in ['{','}','\n','\r'])for name in [start,end])
 t+='set start {'+start+'}\nset end {'+end+'}\n'
 t+='''set sp [get_pins [list $start]];set ep [get_pins [list $end]]
if {[llength $sp]!=1 || [llength $ep]!=1} {error "Missing paired data path $start -> $end"}
set paths [find_timing_paths -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1]
if {[llength $paths]!=1} {error "Missing constrained paired path $start -> $end"}
puts $f "$start\t$end\t[get_property [lindex $paths 0] slack]"
report_checks -from $sp -to $ep -path_delay min -group_path_count 1 -endpoint_path_count 1 -digits 9 -format full_clock_expanded >> selected-min.rpt
'''
t+='close $f\n';(O/'probe.tcl').write_text(t)
with(O/'probe.log').open('w')as log:r=subprocess.run(['openroad','-exit','probe.tcl'],cwd=O,stdout=log,stderr=subprocess.STDOUT)
assert inputs=={str(f):sha(f)for f in files}and all(sha(Path(f))==h for f,h in dr['inputs'].items())
out=[]
if r.returncode==0:
 for line in(O/'selected-min.tsv').read_text().splitlines():
  start,end,slack=line.split('\t');out.append(dict(startpoint=start,endpoint=end,slack_ns=float(slack)))
 assert len(out)==len(pairs)and {(x['startpoint'],x['endpoint'])for x in out}==set(pairs)
receipt=dict(passed=r.returncode==0,physical=str(a.physical),capacity=a.capacity,inputs=inputs,diagnosis=str(a.diagnosis),diagnosis_receipt_sha256=sha(a.diagnosis/'receipt.json'),failing_paths_sha256=sha(a.diagnosis/'failing-paths.tsv'),rows=out,probe_sha256=sha(O/'probe.tcl'),scope='Read-only exact final SPEF paired paths, including complete launch/capture clocks; no qualification transfer or acceptance change.')
(O/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');raise SystemExit(r.returncode)
