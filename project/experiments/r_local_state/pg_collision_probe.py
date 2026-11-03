"""Locate native cells/PG rails at actual final PSM short coordinates."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess
p=argparse.ArgumentParser();p.add_argument('--physical',type=Path,required=True);p.add_argument('--both-power-nets',action='store_true');a=p.parse_args()
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
S=a.physical;binding=json.loads((S/'CLOCK_ROUTE_BINDING.json').read_text());baseline=Path(binding['source_odb']);assert sha(baseline)==binding['source_odb_sha256']
current=S/'flow/results/nangate45/r166_1024/base/6_final.odb';log=S/'flow.log'
inputs={str(f):sha(f)for f in [current,baseline,log,S/'CLOCK_ROUTE_BINDING.json']};O=Path.cwd()/'pg-collision-probe';O.mkdir(exist_ok=False)
text=log.read_text()
if a.both_power_nets:
 t='set_thread_count 16\nread_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib\nread_db {'+str(current)+'}\nforeach net {VDD VSS} {set code [catch {check_power_grid -net $net -error_file ${net}.rpt} message];puts "R166_DIAG_BOTH_PG; net=$net; code=$code; message=$message"}\n'
 (O/'both-pg.tcl').write_text(t)
 with(O/'both-pg.log').open('w')as stream:subprocess.run(['openroad','-no_init','-exit','both-pg.tcl'],cwd=O,stdout=stream,stderr=subprocess.STDOUT,check=True)
 text+='\n'+(O/'both-pg.log').read_text()
 assert all('R166_DIAG_BOTH_PG; net='+net+'; code='in text for net in ['VDD','VSS'])
rows=sorted(set(re.findall(r'Shorted shape on net (\S+) to net (\S+) at \(([0-9.]+)um, ([0-9.]+)um\) - \(([0-9.]+)um, ([0-9.]+)um\), layer: (\S+)\.',text)))
assert rows and len(rows)<=100
r=0
for label,odb in [('baseline',baseline),('current',current)]:
 t='set_thread_count 16\nset f [open cells_'+label+'.tsv w]\nread_db {'+str(odb)+'}\nset block [ord::get_db_block]\nset dbu [$block getDbUnitsPerMicron]\n'
 for index,row in enumerate(rows):
  x1,y1,x2,y2=map(float,row[2:6]);t+='set bounds [list '+str(x1-1)+' '+str(y1-1)+' '+str(x2+1)+' '+str(y2+1)+']\n'
  t+='''foreach inst [$block getInsts] {
 set b [$inst getBBox];lassign $bounds x1 y1 x2 y2
 if {[$b xMin]>$x2*$dbu || [$b xMax]<$x1*$dbu || [$b yMin]>$y2*$dbu || [$b yMax]<$y1*$dbu} {continue}
 set group [$inst getGroup];if {$group ne "NULL"} {set group [$group getName]}
 puts $f [join [list '''+label+' '+str(index)+''' [$inst getName] [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus] $group [$b xMin] [$b yMin] [$b xMax] [$b yMax]] "\t"]
 foreach term [$inst getITerms] {
  if {[[$term getMTerm] getSigType] ni {POWER GROUND}} {continue}
  set net [$term getNet];if {$net ne "NULL"} {set net [$net getName]}
  puts $f [join [list PG [$inst getName] [[$term getMTerm] getName] $net] "\t"]
 }
}
'''
 t+='close $f\n';(O/(label+'.tcl')).write_text(t)
 with(O/(label+'.log')).open('w')as out:run=subprocess.run(['openroad','-no_init','-exit',label+'.tcl'],cwd=O,stdout=out,stderr=subprocess.STDOUT)
 r=run.returncode
 if r:break
if r==0:(O/'cells.tsv').write_bytes(b''.join((O/('cells_'+label+'.tsv')).read_bytes()for label in ['baseline','current']))
assert all(sha(Path(f))==v for f,v in inputs.items())
result=dict(passed=r==0,inputs=inputs,shorts=rows,artifacts={f.name:dict(sha256=sha(f),bytes=f.stat().st_size)for f in O.iterdir()if f.is_file()},qualification=False,scope='Read-only native ownership at actual final PSM shorts; complete original final PG gate remains required.')
(O/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');raise SystemExit(r)
