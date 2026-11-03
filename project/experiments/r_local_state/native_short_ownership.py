"""Read-only native pin/cell ownership for exact whole-die short coordinates."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess
p=argparse.ArgumentParser();p.add_argument('--physical',type=Path,required=True);p.add_argument('--diagnosis',type=Path,required=True);a=p.parse_args()
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
odb=a.physical/'flow/results/nangate45/r166_1024/base/6_final.odb';receipt=a.diagnosis/'receipt.json';report=a.diagnosis/'complete.rpt';r=json.loads(receipt.read_text())
assert r['passed']is False and r['original_odb_sha256']==sha(odb)and r['native_report_sha256']==sha(report)
rows=re.findall(r'violation type: Short\s+srcs: net:(\S+) net:(\S+)\s+bbox = \(([-\d.]+), ([-\d.]+)\) - \(([-\d.]+), ([-\d.]+)\) on Layer (\w+)',report.read_text());assert len(rows)==r['native_drc_count']and 0<len(rows)<=64
O=Path.cwd()/'short-ownership';O.mkdir(exist_ok=False);inputs={str(f):sha(f)for f in [odb,receipt,report]}
t='set_thread_count 16\nread_db {'+str(odb)+'}\nset block [ord::get_db_block];set dbu [$block getDbUnitsPerMicron]\nset f [open ownership.tsv w]\n'
for idx,(n1,n2,x0,y0,x1,y1,layer)in enumerate(rows):
 t+='set bounds [list '+' '.join([x0,y0,x1,y1])+']\n'
 for name in [n1,n2]:
  assert not any(c in name for c in '{}\n\r')
  t+='set net [$block findNet {'+name+'}]\nif {$net eq "NULL"} {error "Short net missing"}\n'
  t+='''foreach term [$net getITerms] {
 set inst [$term getInst];set b [$inst getBBox];lassign $bounds x0 y0 x1 y1
 if {[$b xMin]>($x1+.5)*$dbu || [$b xMax]<($x0-.5)*$dbu || [$b yMin]>($y1+.5)*$dbu || [$b yMax]<($y0-.5)*$dbu} {continue}
 puts $f [join [list CELL '''+str(idx)+''' [$net getName] [$net getSigType] [$inst getName] [[$inst getMaster] getName] [[$term getMTerm] getName] [$inst getLocation] [$inst getOrient] [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "\t"]
 set code [catch {$term getGeometries} geometries]
 if {$code} {puts $f [join [list API_ERROR $geometries] "\t"];continue}
 foreach item $geometries {
  lassign $item lay box
  set code [catch {list [$lay getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]} shape]
  if {$code} {puts $f [join [list API_ERROR $item $shape] "\t"]} else {puts $f [join [list PIN [$inst getName] [[$term getMTerm] getName] $shape] "\t"]}
 }
}
'''
t+='close $f\n';(O/'ownership.tcl').write_text(t)
with(O/'ownership.log').open('w')as log:run=subprocess.run(['openroad','-no_init','-exit','ownership.tcl'],cwd=O,stdout=log,stderr=subprocess.STDOUT)
assert all(sha(Path(n))==h for n,h in inputs.items())
(O/'receipt.json').write_text(json.dumps(dict(passed=run.returncode==0,inputs=inputs,shorts=rows,qualification=False,native_exit=run.returncode,artifacts={f.name:dict(sha256=sha(f),bytes=f.stat().st_size)for f in O.iterdir()if f.is_file()},scope='Read-only actual pin/cell ownership; API_ERROR remains explicit and is not evidence of pin geometry or qualification.'),indent=2)+'\n');raise SystemExit(run.returncode)
