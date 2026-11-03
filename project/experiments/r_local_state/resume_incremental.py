"""Finite final-SPEF data ECO preserving untouched detailed routes before DRT.

Uses the native incremental GRT bracket verified by incremental_route_probe.
Every original final physical/function gate remains independently required.
"""
from pathlib import Path
import argparse,hashlib,json,math,os,re,shutil,subprocess
from continued_clock_routes import prepare
from fixed_clock_routes import audit
from native_interchange import lex

def net_hashes(path):
 active=False;row=[];out={}
 with path.open()as stream:
  for line in stream:
   if not active:
    if re.match(r'^\s*NETS\s+\d+\s*;',line):active=True
    continue
   if re.match(r'^\s*END\s+NETS\s*$',line):assert not row;break
   for token in lex.findall(line):
    if token.startswith('#'):continue
    row.append(token)
    if token==';':
     assert row[0]=='-'and row[1]not in out
     out[row[1]]=hashlib.sha256('\0'.join(row).encode()).hexdigest();row=[]
 assert active and not row and out
 return out

p=argparse.ArgumentParser()
for name in ['source','endpoint-budget','fixed-clock-proof','noop-probe']:p.add_argument('--'+name,type=Path,required=True)
p.add_argument('--pg-placement',type=Path);p.add_argument('--pg-source',type=Path)
a=p.parse_args();sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
assert bool(a.pg_placement)==bool(a.pg_source)
S=a.source;R=S/'flow/results/nangate45/r166_1024/base';P=Path(__file__).resolve().parent
noop=json.loads((a.noop_probe/'receipt.json').read_text());assert noop['passed']and noop['whole_native_def_bytes_identical']and noop['physical']==str(S)and noop['qualification']is False
budget=json.loads((a.endpoint_budget/'receipt.json').read_text());assert budget['passed']and budget.get('hold_selection_threshold_ns',0)==0
diagnosis=Path(budget['diagnosis']);dr=json.loads((diagnosis/'receipt.json').read_text())
assert dr['passed']and dr['inputs']==budget['inputs']and sha(diagnosis/'receipt.json')==budget['diagnosis_receipt_sha256']and sha(diagnosis/'failing-paths.tsv')==budget['failing_paths_sha256']
assert 0<len(budget['rows'])<=1000 and all(row['hold_ns']<0 for row in budget['rows'])
assert json.loads((S/'receipt.json').read_text())['exit']==0
before={str(f):sha(f)for f in [S/'receipt.json',S/'config.mk',R/'6_final.v',a.noop_probe/'receipt.json',a.endpoint_budget/'receipt.json']}
for receipt in [noop,budget]:
 for name,digest in receipt['inputs'].items():assert sha(Path(name))==digest;before[name]=digest
for name,row in noop['artifacts'].items():assert sha(a.noop_probe/name)==row['sha256']
for suffix in ['odb','sdc','spef']:assert budget['inputs'][str(R/('6_final.'+suffix))]==sha(R/('6_final.'+suffix))
delays={}
for row in budget['rows']:
 name=row['endpoint'];count=math.ceil((.040-row['hold_ns'])/.025)
 assert name.endswith('/D')and not any(c in name for c in '{}\n\r')and 1<=count<=8 and row['setup_ns']>count*.040+.020
 assert name not in delays;delays[name]=count
assert sum(delays.values())<=5000
D=Path.cwd()/'physical';D.mkdir(exist_ok=False);T=D/'flow/results/nangate45/r166_1024/base';T.mkdir(parents=True)
files=[f for f in R.iterdir()if f.is_file()and f.name.startswith(('1_','4_'))]
for f in files:before[str(f)]=sha(f);shutil.copyfile(f,T/f.name)
for name in ['input.v','input.sdc','regions.json','pins.tcl','regions.tcl']:
 before[str(S/name)]=sha(S/name);shutil.copyfile(S/name,D/name)
prepare(D,S,a.fixed_clock_proof)
before.update(json.loads((D/'CONTINUED_CLOCK_PREPARE.json').read_text())['inputs'])
shutil.copyfile(P/'buffer_locality.tcl',D/'buffer_locality.tcl')
(D/'extracted_endpoints.tcl').write_text('set r166_endpoint_delays [dict create '+' '.join('{'+n+'} '+str(c)for n,c in delays.items())+']\n'+(P/'extracted_endpoints.tcl').read_text())
(D/'EXTRACTED_ENDPOINT_BINDING.json').write_text(json.dumps(dict(budget=str(a.endpoint_budget),diagnosis=str(diagnosis),budget_receipt_sha256=sha(a.endpoint_budget/'receipt.json'),inputs=budget['inputs'],rows=budget['rows'],endpoint_buffer_counts=delays,scope='Only exact negative final-SPEF data endpoints; finite identity buffers and measured setup headroom. Source untouched routes retained before DRT. Original final acceptance unchanged.'),indent=2)+'\n')
if a.pg_placement:
 from pg_data_placement import prepare as prepare_pg
 old_endpoint=json.loads((a.pg_source/'EXTRACTED_ENDPOINT_BINDING.json').read_text());old_final=json.loads((a.pg_source/'FINAL_RESUME.json').read_text())
 assert old_endpoint['inputs']==budget['inputs']and old_endpoint['endpoint_buffer_counts']==delays and old_final['source_final']==str(S)
 pg_plan=prepare_pg(D,a.pg_source,a.pg_placement);assert pg_plan['pre_route_incremental_checkpoint']
 before.update(pg_plan['inputs'])
(D/'FINAL_RESUME.json').write_text(json.dumps(dict(source_final=str(S),source_final_hashes={str(R/('6_final.'+e)):sha(R/('6_final.'+e))for e in ['odb','sdc','spef','v']},qualification_transferred=False,scope='Exact source final topology and existing detailed data routes. Finite measured endpoint ECO, native incremental GRT, fresh DRT/RCX and all original final gates.'),indent=2)+'\n')
config=(S/'config.mk').read_text().replace(str(S),str(D));(D/'config.mk').write_text(config)
# No full global repair sweep or removal of unrelated regular wires.
t='''set_thread_count 16
read_liberty /OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib
read_db {'''+str(R/'6_final.odb')+'''}
read_sdc {'''+str(R/'6_final.sdc')+'''}
set here {'''+str(D)+'''}
set block [ord::get_db_block];set dbu [$block getDbUnitsPerMicron]
remove_fillers
source {'''+str(D/'buffer_locality.tcl')+'''}
source {'''+str(D/'fixed_clock_prepare.tcl')+'''}
write_def $here/INCREMENTAL_BEFORE.def
read_guides {'''+str(R/'route.guide')+'''}
 set affected [dict create]
foreach name [list '''+' '.join('{'+n+'}'for n in delays)+'''] {
 set slash [string last / $name];set inst [$block findInst [string range $name 0 [expr {$slash-1}]]]
 if {$inst eq "NULL"} {error "Measured data endpoint absent"}
 set net [[$inst findITerm D] getNet]
 if {$net eq "NULL" || [$net getSigType] in {CLOCK POWER GROUND}} {error "Measured endpoint is not a data net"}
 dict set affected [$net getName] 1
}
set f [open $here/INCREMENTAL_AFFECTED_NETS.tsv w]
dict for {name unused} $affected {puts $f $name}
close $f
global_route -start_incremental
source {'''+str(D/'extracted_endpoints.tcl')+'''}
'''
if a.pg_placement:t+='source {'+str(D/'pg_data_placement.tcl')+'}\n'
t+='''
# A modified source net cannot retain a stale wire ending at the old D pin.
# Every other source data wire remains available to detailed routing.
dict for {name unused} $affected {
 set net [$block findNet $name];set wire [$net getWire]
 if {$wire ne "NULL"} {odb::dbWire_destroy $wire}
}
global_route -end_incremental
write_guides {'''+str(T/'route.guide')+'''}
write_def $here/INCREMENTAL_AFTER_GRT.def
write_db {'''+str(T/'5_1_grt.odb')+'''}
write_sdc {'''+str(T/'5_1_grt.sdc')+'''}
'''
if a.pg_placement and pg_plan.get('rerouted_data_nets'):
 marker='set f [open $here/INCREMENTAL_AFFECTED_NETS.tsv w]'
 assert t.count(marker)==1
 t=t.replace(marker,''.join('dict set affected {'+name+'} 1\n'for name in pg_plan['rerouted_data_nets'])+marker)
(D/'incremental.tcl').write_text(t)
commands=[];code=0;env=os.environ.copy();env.update(NUM_CORES='16',OMP_NUM_THREADS='16')
with(D/'flow.log').open('w')as log:
 cmd=['openroad','-no_init','-exit',str(D/'incremental.tcl')];commands.append(cmd);code=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT).returncode
 if code==0:
  old=net_hashes(D/'INCREMENTAL_BEFORE.def');new=net_hashes(D/'INCREMENTAL_AFTER_GRT.def')
  affected=set((D/'INCREMENTAL_AFFECTED_NETS.tsv').read_text().splitlines());assert affected and affected<=set(old)
  assert set(old)<=set(new),'An original net disappeared during incremental routing'
  unchanged=set(old)-affected;changed=[name for name in unchanged if old[name]!=new[name]]
  verification=dict(passed=not changed,original_nets=len(old),finite_affected_original_nets=len(affected),untouched_nets_verified=len(unchanged),changed_untouched_nets=changed,before_def_sha256=sha(D/'INCREMENTAL_BEFORE.def'),after_def_sha256=sha(D/'INCREMENTAL_AFTER_GRT.def'),affected_inventory_sha256=sha(D/'INCREMENTAL_AFFECTED_NETS.tsv'),scope='Every complete untouched original NETS record identical before/after incremental GRT, including all terminals/attributes/routes. Fresh DRT and all original final gates still required.')
  (D/'INCREMENTAL_ROUTE_AUDIT.json').write_text(json.dumps(verification,indent=2)+'\n')
  assert verification['passed'],('Incremental GRT changed untouched original nets',changed[:10])
  (D/'INCREMENTAL_ROUTE_BINDING.json').write_text(json.dumps(dict(inputs=before,noop_probe=str(a.noop_probe),noop_receipt_sha256=sha(a.noop_probe/'receipt.json'),audit_sha256=sha(D/'INCREMENTAL_ROUTE_AUDIT.json'),qualification_transferred=False,scope='Measured finite endpoint ECO; complete untouched native NETS audit required before DRT. No physical qualification transfer.'),indent=2)+'\n')
  for target in ['do-5_2_route','do-5_3_fillcell','do-5_route','do-5_route.sdc','do-6_1_fill','do-6_1_fill.sdc','do-6_report']:
   cmd=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(D/'config.mk'),'WORK_HOME='+str(D/'flow'),target];commands.append(cmd);code=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT).returncode
   if code:break
assert all(sha(Path(f))==h for f,h in before.items())
if(D/'PG_PRE_ROUTE.tsv').exists():
 rows=[r.split('\t')for r in(D/'PG_PRE_ROUTE.tsv').read_text().splitlines()];assert len(rows)==2 and {r[0]for r in rows}=={'VDD','VSS'}
 (D/'PG_PRE_ROUTE.json').write_text(json.dumps(dict(passed=all(r[1:]==['0','1']for r in rows),rows=rows,checkpoint=str(D/'CLOCK_POST_RESTORE.odb'),checkpoint_sha256=sha(D/'CLOCK_POST_RESTORE.odb'),native_tsv_sha256=sha(D/'PG_PRE_ROUTE.tsv'),scope='Pre-DRT PG component only; all final original gates still mandatory.'),indent=2)+'\n')
if code==0:
 audit(D,T/'6_final.def','final')
 old_data=net_hashes(D/'INCREMENTAL_BEFORE.def');final_data=net_hashes(T/'6_final.def')
 clocks={line.split('\t')[0]for line in(a.fixed_clock_proof/'clock-nets.tsv').read_text().splitlines()}
 selected=set((D/'INCREMENTAL_AFFECTED_NETS.tsv').read_text().splitlines())
 other=set(old_data)-clocks-selected;different=sorted(name for name in other if final_data.get(name)!=old_data[name])
 (D/'FINAL_DATA_ROUTE_RETENTION.json').write_text(json.dumps(dict(before_def_sha256=sha(D/'INCREMENTAL_BEFORE.def'),final_def_sha256=sha(T/'6_final.def'),original_unselected_nonclock_nets=len(other),identical_complete_records=len(other)-len(different),changed_or_missing_records=different,scope='Measured complete original nonclock NETS-record retention after actual DRT/final export. Conservative exact-record comparison, not a timing or DRC acceptance waiver. All original independent final gates remain required.'),indent=2)+'\n')
 if a.pg_placement:
  from pg_data_placement import verify_final
  verify_final(D,T/'6_final.def')
(D/'receipt.json').write_text(json.dumps(dict(capacity=1024,exit=code,source_final=str(S),source_unchanged=True,source_hashes=before,commands=commands,qualification_transferred=False,passed=False,acceptance_sdc_unchanged=sha(S/'input.sdc')==sha(D/'input.sdc'),change='Exact final source finite measured data ECO using native incremental GRT. Fresh DRT/RCX and original full final gates required.'),indent=2)+'\n')
raise SystemExit(code)
