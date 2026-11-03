"""Reroute only data nets named by an immutable failed whole-die short report.

Temporary local routing keepouts cover the measured collision rectangles. They
are removed before the final database is exported; no rule/marker is excluded.
Every original final timing, native/GDS, power and function gate remains needed.
"""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess
from decimal import Decimal
from continued_clock_routes import prepare
from fixed_clock_routes import audit

p=argparse.ArgumentParser()
for name in ['source','diagnosis','fixed-clock-proof','hook-proof']:p.add_argument('--'+name,type=Path,required=True)
p.add_argument('--clearance',type=Decimal,default=Decimal('.14'));p.add_argument('--placement',type=Path);a=p.parse_args()
assert Decimal('0')<a.clearance<=Decimal('1')
S=a.source;R=S/'flow/results/nangate45/r166_1024/base';P=Path(__file__).resolve().parent
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
dr=json.loads((a.diagnosis/'receipt.json').read_text());report=a.diagnosis/'complete.rpt'
assert dr['passed']is False and dr['native_drc_count']>0 and dr['no_marker_or_rule_exclusions']and dr['original_source_unchanged']and dr['identical_geometry_and_connections']
assert dr['original_odb_sha256']==sha(R/'6_final.odb')and dr['native_report_sha256']==sha(report)
pattern=r'violation type: Short\s+srcs: net:(\S+) net:(\S+)\s+bbox = \(([-\d.]+), ([-\d.]+)\) - \(([-\d.]+), ([-\d.]+)\) on Layer (\w+)'
rows=re.findall(pattern,report.read_text());assert len(rows)==dr['native_drc_count']and 1<=len(rows)<=64
assert report.read_text().count('violation type:')==len(rows)
assert all(not any(c in n for c in '{}\n\r\t')for row in rows for n in row[:2])
inputs={str(f):sha(f)for f in [R/('6_final.'+e)for e in ['odb','sdc','spef','v']]+[a.diagnosis/'receipt.json',report,S/'receipt.json',S/'config.mk']}
assert json.loads((S/'receipt.json').read_text())['exit']==0
hr=json.loads((a.hook_proof/'receipt.json').read_text());assert hr['passed']is True and hr['native_exit']==0 and hr['physical']==str(S)and hr['qualification']is False and hr['checks']and all(hr['checks'].values())
assert hr['hook_sha256']==sha(P/'short_obstruction_hooks.py')
for name,digest in hr['inputs'].items():assert sha(Path(name))==digest;inputs[name]=digest
for name,item in hr['artifacts'].items():
 f=a.hook_proof/name;assert sha(f)==item['sha256']and f.stat().st_size==item['bytes'];inputs[str(f)]=item['sha256']
inputs[str(a.hook_proof/'receipt.json')]=sha(a.hook_proof/'receipt.json')
placement=None;moves=[]
if a.placement:
 placement=json.loads((a.placement/'receipt.json').read_text())
 assert placement['passed']is True and placement['native_exit']==0 and placement['qualification']is False and placement['physical']==str(S)
 assert placement['native_short_ownership']and placement['retain_data_routes']and placement['clock_audit']['passed']and not placement['pre_route_checkpoint']
 ownership=Path(placement['diagnosis']);orec=json.loads((ownership/'receipt.json').read_text())
 assert orec['passed']and orec['inputs'][str(a.diagnosis/'receipt.json')]==sha(a.diagnosis/'receipt.json')and orec['inputs'][str(report)]==sha(report)
 for name,digest in placement['inputs'].items():assert sha(Path(name))==digest;inputs[name]=digest
 for name,item in placement['artifacts'].items():
  f=a.placement/name;assert sha(f)==item['sha256']and f.stat().st_size==item['bytes'];inputs[str(f)]=item['sha256']
 inputs[str(a.placement/'receipt.json')]=sha(a.placement/'receipt.json')
 plog=(a.placement/'probe.log').read_text()
 assert all('R166_PG_PLACEMENT_CHECK; net='+net+'; code=0; message=1'in plog for net in ['VDD','VSS'])
 moves=[line.split('\t')for line in(a.placement/'moves.tsv').read_text().splitlines()]
 assert len(moves)==len(placement['selected_cells'])and 0<len(moves)<=64 and {r[0]for r in moves}==set(placement['selected_cells'])
 for row in moves:
  assert len(row)==8 and not any(c in row[0]for c in '{}\n\r\t')
  assert all(str(int(v))==v for v in row[2:6])and int(row[7])>0 and row[6]in ['MX','R0']
  cell=placement['selected_cells'][row[0]];assert row[1]==cell['master']and ' '.join(row[2:4])==cell['location']and row[6]==cell['orient']and not row[1].startswith(('DFF','FILLCELL','TAPCELL'))
D=Path.cwd()/'physical';D.mkdir(exist_ok=False);T=D/'flow/results/nangate45/r166_1024/base';T.mkdir(parents=True)
for f in R.iterdir():
 if f.is_file()and f.name.startswith(('1_','4_')):inputs[str(f)]=sha(f);shutil.copyfile(f,T/f.name)
for name in ['input.v','input.sdc','regions.json','pins.tcl','regions.tcl']:
 inputs[str(S/name)]=sha(S/name);shutil.copyfile(S/name,D/name)
prepare(D,S,a.fixed_clock_proof)
inputs.update(json.loads((D/'CONTINUED_CLOCK_PREPARE.json').read_text())['inputs'])
shutil.copyfile(R/'route.guide',T/'route.guide');inputs[str(R/'route.guide')]=sha(R/'route.guide')
(D/'config.mk').write_text((S/'config.mk').read_text().replace(str(S),str(D)))
(D/'FINAL_RESUME.json').write_text(json.dumps(dict(source_final=str(S),source_final_hashes={str(R/('6_final.'+e)):sha(R/('6_final.'+e))for e in ['odb','sdc','spef','v']},qualification_transferred=False,scope='Measured whole-die short data reroute only. No clock/RTL/ISA change. All final gates rerun.'),indent=2)+'\n')
pairlist=' '.join('[list {'+x+'} {'+y+'}]'for x,y,*_ in rows)
t='''set_thread_count 16
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db {'''+str(R/'6_final.odb')+'''}
read_sdc {'''+str(R/'6_final.sdc')+'''}
set here {'''+str(D)+'''}
set block [ord::get_db_block]
remove_fillers
source {'''+str(D/'fixed_clock_prepare.tcl')+'''}
set data [dict create]
set f [open $here/SHORT_NET_CLASSES.tsv w]
foreach pair [list '''+pairlist+'''] {
 set clocks 0;set signals 0
 foreach name $pair {
  set net [$block findNet $name]
  if {$net eq "NULL"} {error "Measured short net missing"}
  set kind [$net getSigType];puts $f "$name\t$kind"
  if {$kind eq "CLOCK"} {incr clocks} elseif {$kind eq "SIGNAL"} {incr signals;dict set data $name 1} else {error "Short is not data-clock"}
 }
 if {$clocks!=1 || $signals!=1} {error "Expected one data and one fixed clock net"}
}
close $f
set f [open $here/SHORT_DATA_NETS.tsv w]
dict for {name unused} $data {
 set net [$block findNet $name];set wire [$net getWire]
 if {$wire eq "NULL"} {error "Measured data wire absent"}
 odb::dbWire_destroy $wire;puts $f $name
}
close $f
write_db {'''+str(T/'5_1_grt.odb')+'''}
write_sdc {'''+str(T/'5_1_grt.sdc')+'''}
'''
if placement:
 marker='set f [open $here/SHORT_DATA_NETS.tsv w]';assert t.count(marker)==1
 moving='''read_guides {'''+str(R/'route.guide')+'''}
set before [dict create]
foreach inst [$block getInsts] {dict set before [$inst getName] [list [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient]]}
global_route -start_incremental
set moved [dict create]
set f [open $here/SHORT_MOVED_CELL_NETS.tsv w]
'''
 for name,master,x,y,nx,ny,orient,pitch in moves:
  moving+='set inst [$block findInst {'+name+'}]\n'
  moving+='if {$inst eq "NULL" || [[$inst getMaster] getName] ne {'+master+'} || [$inst getLocation] ne {'+x+' '+y+'} || [$inst getOrient] ne {'+orient+'}} {error "Measured cell placement source differs"}\n'
  moving+='$inst setPlacementStatus PLACED\n$inst setLocation '+nx+' '+ny+'\n$inst setPlacementStatus LOCKED\ndict set moved {'+name+'} 1\n'
  moving+='''foreach term [$inst getITerms] {
 set net [$term getNet];if {$net eq "NULL"} {continue}
 set kind [$net getSigType]
 if {$kind in {POWER GROUND}} {continue}
 if {$kind ne "SIGNAL"} {error "Measured combinational cell has a clock connection"}
 dict set data [$net getName] 1
 puts $f [join [list [$inst getName] [$net getName] $kind] "\t"]
}
'''
 for name in placement.get('rerouted_data_nets',[]):
  assert not any(c in name for c in '{}\n\r\t')
  moving+='set net [$block findNet {'+name+'}]\nif {$net eq "NULL" || [$net getSigType] ne "SIGNAL" || [$net getWire] eq "NULL"} {error "Measured additional PG wire is not routed data"}\ndict set data {'+name+'} 1\n'
 moving+='close $f\n'
 t=t.replace(marker,moving+marker)
 marker='write_db {'+str(T/'5_1_grt.odb')+'}';assert t.count(marker)==1
 t=t.replace(marker,'''global_route -end_incremental
foreach inst [$block getInsts] {
 set name [$inst getName]
 if {![dict exists $moved $name] && [dict get $before $name] ne [list [[$inst getMaster] getName] [$inst getLocation] [$inst getOrient]]} {error "An unselected original cell changed"}
}
write_guides {'''+str(T/'route.guide')+'''}
'''+marker)
(D/'short_prepare.tcl').write_text(t)
from short_obstruction_hooks import hooks
obstructions=[]if placement else rows
keepout,remove=hooks(D,obstructions,a.clearance)
hook=D/'fixed_clock_before-detail.tcl';hook.write_text(hook.read_text()+keepout)
hook=D/'fixed_clock_after-detail.tcl';hook.write_text(remove+hook.read_text())
binding=dict(inputs=inputs,diagnosis=str(a.diagnosis),diagnosis_receipt_sha256=sha(a.diagnosis/'receipt.json'),hook_proof=str(a.hook_proof),hook_receipt_sha256=sha(a.hook_proof/'receipt.json'),shorts=rows,clearance_um=str(a.clearance),temporary_obstruction_count=len(obstructions),temporary_obstructions_only=True,qualification_transferred=False,scope='Measured data-only reroute, original clock geometry audited unchanged. Temporary keepouts, if used, removed before final export. All original final gates mandatory.')
if placement:binding.update(placement_probe=str(a.placement),placement_receipt_sha256=sha(a.placement/'receipt.json'),moves=moves,scope='Exactly replay PG/clock/placement-passed bounded combinational-cell moves; remove only incident data routes and original measured short data routes. Native incremental GRT, no temporary keepouts, all original clocks/other cell positions retained. All original final gates mandatory.')
(D/'LOCAL_SHORT_ROUTE_BINDING.json').write_text(json.dumps(binding,indent=2)+'\n')
env=os.environ.copy();env.update(NUM_CORES='16',OMP_NUM_THREADS='16');commands=[];code=0
with(D/'flow.log').open('w')as log:
 cmd=['openroad','-no_init','-exit',str(D/'short_prepare.tcl')];commands.append(cmd);code=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT).returncode
 if code==0:
  for target in ['do-5_2_route','do-5_3_fillcell','do-5_route','do-5_route.sdc','do-6_1_fill','do-6_1_fill.sdc','do-6_report']:
   cmd=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(D/'config.mk'),'WORK_HOME='+str(D/'flow'),target];commands.append(cmd);code=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT).returncode
   if code==0 and target=='do-5_2_route':
    dm=json.loads((D/'flow/logs/nangate45/r166_1024/base/5_2_route.json').read_text())
    if dm['detailedroute__route__drc_errors']!=0:code=2
   if code:break
assert all(sha(Path(n))==h for n,h in inputs.items())
if(D/'PG_PRE_ROUTE.tsv').exists():
 pg=[r.split('\t')for r in(D/'PG_PRE_ROUTE.tsv').read_text().splitlines()];assert len(pg)==2 and {r[0]for r in pg}=={'VDD','VSS'}
 (D/'PG_PRE_ROUTE.json').write_text(json.dumps(dict(passed=all(r[1:]==['0','1']for r in pg),rows=pg,checkpoint=str(D/'CLOCK_POST_RESTORE.odb'),checkpoint_sha256=sha(D/'CLOCK_POST_RESTORE.odb'),native_tsv_sha256=sha(D/'PG_PRE_ROUTE.tsv'),scope='Pre-DRT component only, final gates mandatory.'),indent=2)+'\n')
if code==0:
 audit(D,T/'6_final.def','final')
 removed=(D/'SHORT_TEMP_OBSTRUCTIONS_REMOVED.tsv').read_text().split();assert int(removed[0])==len(obstructions)and removed[1]==removed[2]
(D/'receipt.json').write_text(json.dumps(dict(capacity=1024,exit=code,source_final=str(S),source_unchanged=True,source_hashes=inputs,commands=commands,qualification_transferred=False,passed=False,acceptance_sdc_unchanged=sha(S/'input.sdc')==sha(D/'input.sdc'),change='Finite actual native-short data reroute; temporary local keepouts removed; original final gates mandatory.'),indent=2)+'\n')
raise SystemExit(code)
