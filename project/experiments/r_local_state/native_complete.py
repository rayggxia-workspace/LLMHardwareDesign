"""Whole-die native rule diagnostic with no artificial interior clipping boundary.

Only the in-memory checking grid changes; original ODB, geometry, rules and
fragmented report remain immutable. Fresh short/spacing/notch controls must fail.
"""
from pathlib import Path
from itertools import zip_longest
import argparse, hashlib, json, subprocess, shutil, re

p=argparse.ArgumentParser();p.add_argument('--physical',type=Path,required=True);p.add_argument('--capacity',type=int,required=True);p.add_argument('--checker-root',type=Path);p.add_argument('--source-recheck',type=Path);a=p.parse_args()
R=a.physical/'flow/results/nangate45'/('r166_'+str(a.capacity))/'base'
O=Path.cwd()/'native-complete';O.mkdir(exist_ok=False)
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
odb=R/'6_final.odb';before=sha(odb)
tech=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.tech.lef')
checker=Path(shutil.which('openroad')).resolve();original_checker=checker;tool={'binary':str(checker),'binary_sha256':sha(checker),'kind':'original-container'}
if a.checker_root:
 root=a.checker_root.resolve()
 assert root.parent==Path('/public/home/yuzelu/opt/eda')and root.name.startswith('r166-openroad-gc-cache-')
 build=json.loads((root/'BUILD_RECEIPT.json').read_text());sources=json.loads((root/'UPSTREAM_SOURCES.json').read_text())
 assert build['passed']is True and build['sources']==sources
 assert sources[0]['repository']=='The-OpenROAD-Project/OpenROAD'and sources[0]['commit']=='2eba27b2c602b3b1a8f0fdc7773a5387d58fddaa'
 checker=root/'install/bin/openroad';assert sha(checker)==build['binary_sha256']
 assert a.source_recheck,'Pinned checker requires post-build source verification'
 post=json.loads(a.source_recheck.read_text());assert post['passed']and post['root']==str(root)and post['binary_sha256']==sha(checker)and post['build_receipt_sha256']==sha(root/'BUILD_RECEIPT.json')
 shutil.copyfile(a.source_recheck,O/'CHECKER_SOURCE_RECHECK.json')
 shutil.copyfile(root/'BUILD_RECEIPT.json',O/'CHECKER_BUILD_RECEIPT.json')
 shutil.copyfile(root/'UPSTREAM_SOURCES.json',O/'CHECKER_UPSTREAM_SOURCES.json')
 tool=dict(binary=str(checker),binary_sha256=sha(checker),kind='pinned-unmodified-upstream',root=str(root),build_receipt_sha256=sha(O/'CHECKER_BUILD_RECEIPT.json'),sources_sha256=sha(O/'CHECKER_UPSTREAM_SOURCES.json'))
 tool['post_source_sha256']=sha(O/'CHECKER_SOURCE_RECHECK.json')
(O/'CHECKER_IDENTITY.json').write_text(json.dumps(tool,indent=2)+'\n')
def run(name,tcl,binary=None):
 script=O/(name+'.tcl');script.write_text(tcl)
 with(O/(name+'.log')).open('w')as log:subprocess.run([str(binary or checker),'-no_init','-exit',str(script)],cwd=O,stdout=log,stderr=subprocess.STDOUT,check=True)

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
 if a.checker_root:
  old=name+'-original'
  run(old,'set_thread_count 16\nread_lef {'+str(tech)+'}\nread_def {'+str(definition)+'}\ndrt::check_drc_cmd '+old+'.rpt 0 0 0 0 '+old+'\n',original_checker)
  original=(O/(old+'.rpt')).read_text()
  assert sorted(re.findall(r'^violation type: (.+)$',report,re.M))==sorted(re.findall(r'^violation type: (.+)$',original,re.M)),('Checker fixture result changed',name)
  controls[name]['original_report_sha256']=sha(O/(old+'.rpt'))

if a.checker_root:
 # The optimized routine handles fixed-pin corners. Wire-only controls do
 # not exercise that branch, so also compare two fixed pins per net/layer.
 from native_fixed_fixtures import definitions
 fixed_lef,fixed=definitions(O)
 for name,(definition,violation)in fixed.items():
  df=O/(name+'.def');df.write_text(definition)
  head='set_thread_count 16\nread_lef {'+str(tech)+'}\nread_lef {'+str(fixed_lef)+'}\nread_def {'+str(df)+'}\n'
  run(name,head+'drt::check_drc_cmd '+name+'.rpt 0 0 0 0 '+name+'\n')
  old=name+'-original';run(old,head+'drt::check_drc_cmd '+old+'.rpt 0 0 0 0 '+old+'\n',original_checker)
  report=(O/(name+'.rpt')).read_text();original=(O/(old+'.rpt')).read_text()
  assert (not report.strip())if violation is None else('violation type: '+violation)in report
  assert sorted(re.findall(r'^violation type: (.+)$',report,re.M))==sorted(re.findall(r'^violation type: (.+)$',original,re.M))
  controls[name]=dict(passed=True,expected=violation,report_sha256=sha(O/(name+'.rpt')),original_report_sha256=sha(O/(old+'.rpt')),fixture_lef_sha256=sha(fixed_lef),fixture_def_sha256=sha(df))

interchange=None
load='set_thread_count 16\nread_db {'+str(odb)+'}\n'
if a.checker_root:
 from native_interchange import prepare
 load,interchange=prepare(O,odb,original_checker,checker,run)
t=load+'''
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
'''
run('complete',t)
if interchange:
 assert sha(O/'before.def')==interchange['files']['bridge-reloaded.def']['sha256'],'Whole-die check loaded a different interchange view'
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
assert sha(checker)==tool['binary_sha256']
rec=dict(passed=not report.strip(),checker=tool,original_odb_sha256=before,original_source_unchanged=True,identical_geometry_and_connections=True,non_grid_def_sha256=kept.hexdigest(),before_grid=ga,complete_grid=gb,no_marker_or_rule_exclusions=True,controls=controls,technology_sha256=sha(tech),native_drc_count=report.count('violation type:'),native_report_sha256=sha(O/'complete.rpt'),scope='Complete native rules from the explicitly bound checker over the exact whole die in one partition; no marker filtering. Original fragmented diagnostics and independent complete unmodified original GDS rules remain mandatory. A pinned upstream checker is a distinct tool version, never reported as an original-container pass.')
if interchange:rec['interchange_receipt_sha256']=sha(O/'INTERCHANGE_RECEIPT.json')
(O/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n');assert rec['passed']
