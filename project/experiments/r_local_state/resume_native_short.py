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
for name in ['source','diagnosis','fixed-clock-proof']:p.add_argument('--'+name,type=Path,required=True)
p.add_argument('--clearance',type=Decimal,default=Decimal('.14'));a=p.parse_args()
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
(D/'short_prepare.tcl').write_text(t)
keepout='''
# Temporary local router input only. Exact IDs/coordinates are verified and
# removed by POST_DETAIL_ROUTE before the final ODB/DEF/GDS acceptance views.
set r166_short_obstructions {}
set block [ord::get_db_block]
set r166_original_obstructions [llength [$block getObstructions]]
set f [open $here/SHORT_TEMP_OBSTRUCTIONS.tsv w]
set dbu [$block getDbUnitsPerMicron]
'''
for _,_,x0,y0,x1,y1,layer in rows:
 coords=[Decimal(x0)-a.clearance,Decimal(y0)-a.clearance,Decimal(x1)+a.clearance,Decimal(y1)+a.clearance]
 keepout+='set layer [[ord::get_db_tech] findLayer {'+layer+'}]\nif {$layer eq "NULL"} {error "Short layer absent"}\n'
 keepout+='set rect [list '+' '.join('[expr {round('+str(c)+'*$dbu)}]'for c in coords)+']\n'
 keepout+='set obs [odb::dbObstruction_create $block $layer {*}$rect]\nif {$obs eq "NULL"} {error "Keepout creation failed"}\nlappend r166_short_obstructions [list $obs $layer $rect]\nputs $f "[$obs getId]\\t[$layer getName]\\t$rect"\n'
keepout+='close $f\nif {[llength [$block getObstructions]]!=$r166_original_obstructions+[llength $r166_short_obstructions]} {error "Unexpected obstruction changes"}\n'
hook=D/'fixed_clock_before-detail.tcl';hook.write_text(hook.read_text()+keepout)
remove='''set block [ord::get_db_block]
foreach row $r166_short_obstructions {
 lassign $row obs layer rect
 set box [$obs getBBox]
 if {[$obs getTechLayer] ne $layer || [list [$box xMin] [$box yMin] [$box xMax] [$box yMax]] ne $rect} {error "Temporary keepout identity changed"}
 odb::dbObstruction_destroy $obs
}
if {[llength [$block getObstructions]]!=$r166_original_obstructions} {error "Temporary keepout removal incomplete"}
set f [open $here/SHORT_TEMP_OBSTRUCTIONS_REMOVED.tsv w];puts $f "[llength $r166_short_obstructions]\\t$r166_original_obstructions\\t[llength [$block getObstructions]]";close $f
'''
hook=D/'fixed_clock_after-detail.tcl';hook.write_text(remove+hook.read_text())
(D/'LOCAL_SHORT_ROUTE_BINDING.json').write_text(json.dumps(dict(inputs=inputs,diagnosis=str(a.diagnosis),diagnosis_receipt_sha256=sha(a.diagnosis/'receipt.json'),shorts=rows,clearance_um=str(a.clearance),temporary_obstructions_only=True,qualification_transferred=False,scope='Only measured SIGNAL nets removed; clock classification checked natively, all original clock geometry audited unchanged. Finite local keepouts removed before final export. All original final gates mandatory.'),indent=2)+'\n')
env=os.environ.copy();env.update(NUM_CORES='16',OMP_NUM_THREADS='16');commands=[];code=0
with(D/'flow.log').open('w')as log:
 cmd=['openroad','-no_init','-exit',str(D/'short_prepare.tcl')];commands.append(cmd);code=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT).returncode
 if code==0:
  for target in ['do-5_2_route','do-5_3_fillcell','do-5_route','do-5_route.sdc','do-6_1_fill','do-6_1_fill.sdc','do-6_report']:
   cmd=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(D/'config.mk'),'WORK_HOME='+str(D/'flow'),target];commands.append(cmd);code=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT).returncode
   if code:break
assert all(sha(Path(n))==h for n,h in inputs.items())
if(D/'PG_PRE_ROUTE.tsv').exists():
 pg=[r.split('\t')for r in(D/'PG_PRE_ROUTE.tsv').read_text().splitlines()];assert len(pg)==2 and {r[0]for r in pg}=={'VDD','VSS'}
 (D/'PG_PRE_ROUTE.json').write_text(json.dumps(dict(passed=all(r[1:]==['0','1']for r in pg),rows=pg,checkpoint=str(D/'CLOCK_POST_RESTORE.odb'),checkpoint_sha256=sha(D/'CLOCK_POST_RESTORE.odb'),native_tsv_sha256=sha(D/'PG_PRE_ROUTE.tsv'),scope='Pre-DRT component only, final gates mandatory.'),indent=2)+'\n')
if code==0:
 audit(D,T/'6_final.def','final')
 removed=(D/'SHORT_TEMP_OBSTRUCTIONS_REMOVED.tsv').read_text().split();assert int(removed[0])==len(rows)and removed[1]==removed[2]
(D/'receipt.json').write_text(json.dumps(dict(capacity=1024,exit=code,source_final=str(S),source_unchanged=True,source_hashes=inputs,commands=commands,qualification_transferred=False,passed=False,acceptance_sdc_unchanged=sha(S/'input.sdc')==sha(D/'input.sdc'),change='Finite actual native-short data reroute; temporary local keepouts removed; original final gates mandatory.'),indent=2)+'\n')
raise SystemExit(code)
