"""Whole-die native rule diagnostic with no artificial interior clipping boundary.

Only the in-memory checking grid changes; original ODB, geometry, rules and
fragmented report remain immutable. Fresh short/spacing/notch controls must fail.
"""
from pathlib import Path
from itertools import zip_longest
import argparse, hashlib, json, subprocess

p=argparse.ArgumentParser();p.add_argument('--physical',type=Path,required=True);p.add_argument('--capacity',type=int,required=True);a=p.parse_args()
R=a.physical/'flow/results/nangate45'/('r166_'+str(a.capacity))/'base'
O=Path.cwd()/'native-complete';O.mkdir(exist_ok=False)
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
odb=R/'6_final.odb';before=sha(odb)
tech=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef')
def run(name,tcl):
 script=O/(name+'.tcl');script.write_text(tcl)
 with(O/(name+'.log')).open('w')as log:subprocess.run(['openroad','-no_init','-exit',str(script)],cwd=O,stdout=log,stderr=subprocess.STDOUT,check=True)

controls={}
header='VERSION 5.8 ;\nDIVIDERCHAR "/" ;\nBUSBITCHARS "[]" ;\nDESIGN r166_native_control ;\nUNITS DISTANCE MICRONS 2000 ;\nDIEAREA ( 0 0 ) ( 20000 20000 ) ;\nGCELLGRID X 0 DO 2 STEP 20000 ;\nGCELLGRID Y 0 DO 2 STEP 20000 ;\n'
fixtures={
 'positive':('NETS 1 ;\n- a + USE SIGNAL + ROUTED metal2 ( 8000 4000 ) ( 8000 10000 ) ( 8400 10000 ) ( 8400 4000 ) ;\nEND NETS\n',None),
 'short':('NETS 2 ;\n- a + USE SIGNAL + ROUTED metal2 ( 4000 6000 ) ( 12000 6000 ) ;\n- b + USE SIGNAL + ROUTED metal2 ( 8000 4000 ) ( 8000 10000 ) ;\nEND NETS\n','Short'),
 'spacing':('NETS 2 ;\n- a + USE SIGNAL + ROUTED metal2 ( 8000 4000 ) ( 8000 10000 ) ;\n- b + USE SIGNAL + ROUTED metal2 ( 8200 4000 ) ( 8200 10000 ) ;\nEND NETS\n','Metal Spacing'),
 'notch':('NETS 1 ;\n- a + USE SIGNAL + ROUTED metal2 ( 8000 4000 ) ( 8000 10000 ) ( 8200 10000 ) ( 8200 4000 ) ;\nEND NETS\n','Metal Spacing')}
for name,(body,violation)in fixtures.items():
 definition=O/(name+'.def');definition.write_text(header+body+'END DESIGN\n')
 run(name,'set_thread_count 16\nread_lef {'+str(tech)+'}\nread_def {'+str(definition)+'}\ndrt::check_drc_cmd '+name+'.rpt 0 0 0 0 '+name+'\n')
 report=(O/(name+'.rpt')).read_text()
 assert (not report.strip())if violation is None else('violation type: '+violation)in report,(name,report)
 controls[name]=dict(passed=True,expected=violation,report_sha256=sha(O/(name+'.rpt')))

t='''set_thread_count 16
read_db {%s}
set b [ord::get_db_block];set die [$b getDieArea];set g [$b getGCellGrid]
if {[$die xMin]!=0 || [$die yMin]!=0 || [$die xMax]!=[$die yMax]} {error "Unexpected die"}
write_def before.def
set gx {};set gy {}
for {set i 0} {$i<[$g getNumGridPatternsX]} {incr i} {lappend gx [$g getGridPatternX $i]}
for {set i 0} {$i<[$g getNumGridPatternsY]} {incr i} {lappend gy [$g getGridPatternY $i]}
$g resetGrid
$g addGridPatternX 0 2 [$die xMax]
$g addGridPatternY 0 2 [$die yMax]
if {[$g getGridX] ne [list 0 [$die xMax]] || [$g getGridY] ne [list 0 [$die yMax]]} {error "Incomplete check coverage"}
write_def complete-before.def
drt::check_drc_cmd complete.rpt 0 0 0 0 complete_die
write_def complete-after.def
$g resetGrid
foreach row $gx {lassign $row origin count step;$g addGridPatternX $origin $count $step}
foreach row $gy {lassign $row origin count step;$g addGridPatternY $origin $count $step}
write_def after.def
puts COMPLETE_NATIVE_DIAGNOSTIC_FINISHED
'''%str(odb)
run('complete',t)
assert sha(odb)==before and sha(O/'before.def')==sha(O/'after.def')
assert sha(O/'complete-before.def')==sha(O/'complete-after.def')
kept=hashlib.sha256();grids=[]
def filtered(f,grid):
 for line in f.open('rb'):
  if line.startswith(b'GCELLGRID '):grid.append(line.decode().strip())
  else:yield line
ga=[];gb=[]
for x,y in zip_longest(filtered(O/'before.def',ga),filtered(O/'complete-before.def',gb)):
 assert x is not None and x==y,'Physical shape or connectivity changed';kept.update(x)
assert len(gb)==2 and all(' DO 2 STEP 'in s for s in gb)
report=(O/'complete.rpt').read_text()
rec=dict(passed=not report.strip(),original_odb_sha256=before,original_source_unchanged=True,identical_geometry_and_connections=True,non_grid_def_sha256=kept.hexdigest(),before_grid=ga,complete_grid=gb,no_marker_or_rule_exclusions=True,controls=controls,technology_sha256=sha(tech),native_drc_count=report.count('violation type:'),native_report_sha256=sha(O/'complete.rpt'),scope='Complete unchanged native rules over exact whole die in one checking partition; original fragmented diagnostics and independent complete GDS rules remain mandatory.')
(O/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');assert rec['passed']
