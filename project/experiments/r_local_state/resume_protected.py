"""Preserve accepted short-pin input protection and add measured setup margin before rerouting."""
from pathlib import Path
import argparse,subprocess,json,hashlib,os,shutil,re
p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--capacity',type=int,required=True);p.add_argument('--from-final',action='store_true');p.add_argument('--path-evidence',type=Path);p.add_argument('--short-clock',action='store_true');p.add_argument('--measured-grt-reserve',type=Path);p.add_argument('--lower-reserve',type=float,choices=[0.3,0.5],default=0.5);p.add_argument('--buffer-locality',action='store_true');p.add_argument('--io-search-um','--io-search-sites',dest='io_search_um',type=int,choices=[10,50],default=10,help='OpenROAD max_displacement in microns; old sites spelling retained only as a historical CLI alias');p.add_argument('--grt-closure-evidence',type=Path);p.add_argument('--measured-input-evidence',type=Path);p.add_argument('--endpoint-budget',type=Path);p.add_argument('--hold-batch-iterations',type=int,choices=[200,500]);p.add_argument('--grt-hold-goal',type=float,choices=[0.0,0.060],default=0.060);a=p.parse_args()
assert a.lower_reserve==0.5 or a.measured_grt_reserve
assert not a.hold_batch_iterations or a.grt_closure_evidence
assert a.grt_hold_goal==0.060 or (a.grt_closure_evidence and not a.hold_batch_iterations)
S=a.source;D=Path.cwd()/'physical';D.mkdir(exist_ok=False);N='r166_'+str(a.capacity);R=S/'flow/results/nangate45'/N/'base';T=D/'flow/results/nangate45'/N/'base';T.mkdir(parents=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
names=['4_cts.odb','4_cts.sdc','1_synth.odb','1_synth.sdc','1_synth_lec.v','1_2_yosys.v','1_2_yosys.sdc'];protected=[R/n for n in names]+[S/n for n in ['input.v','input.sdc','config.mk']]
if a.from_final:
 assert a.capacity==1024 and a.endpoint_budget and a.buffer_locality and not(a.path_evidence or a.measured_input_evidence or a.short_clock)and a.io_search_um==10
 assert json.loads((S/'receipt.json').read_text())['exit']==0
 final_budget=json.loads((a.endpoint_budget/'receipt.json').read_text());assert final_budget['passed']
 assert all(final_budget['inputs'].get(str(R/('6_final.'+e)))==sha(R/('6_final.'+e))for e in ['odb','sdc','spef']), 'Final topology must be the exact diagnosed source'
 protected.extend(R/('6_final.'+e)for e in ['odb','sdc','spef','v'])
before={str(f):sha(f)for f in protected}
for n in names:shutil.copyfile(R/('6_final.'+n.rsplit('.',1)[1]if a.from_final and n.startswith('4_cts.')else n),T/n)
for n in ['input.v','input.sdc','pins.tcl','regions.tcl','regions.json','defer_hold.tcl','mirror_legalize.tcl','hold_endpoints.tcl','input_hold.tcl']:shutil.copyfile(S/n,D/n)
if a.from_final:
 # Reuse the exact final topology, placements, clock tree and IO drivers.
 # Only fillers/regular wires are removed for a fresh full routing/RCX run.
 (D/'io_protect.tcl').write_text('''set here [file dirname [file normalize [info script]]]
set block [ord::get_db_block]
set dbu [$block getDbUnitsPerMicron]
remove_fillers
set removed 0
foreach net [$block getNets] {
 if {[$net getSigType] in {POWER GROUND}} {continue}
 set wire [$net getWire]
 if {$wire ne "NULL"} {odb::dbWire_destroy $wire;incr removed}
}
puts "R166_EXACT_FINAL_TOPOLOGY_RESUME; removed_regular_wires=$removed; no_IO_or_clock_reinsertion=1; original_final_gates_required=1"
''')
 (D/'FINAL_RESUME.json').write_text(json.dumps(dict(source_final=str(S),source_final_hashes={str(R/('6_final.'+e)):sha(R/('6_final.'+e))for e in ['odb','sdc','spef','v']},qualification_transferred=False,scope='Reuse measured final topology and placement, including previous finite IO/electrical repairs. Only new measured endpoint identity buffers; fresh complete routing/RCX and every original gate required.'),indent=2)+'\n')
else:shutil.copyfile(Path(__file__).parent/'io_protect.tcl',D/'io_protect.tcl')
if a.io_search_um!=10:
 #166 placed all original cells unchanged but three new IO drivers overlapped
 #after the10um search. Widen only their horizontal legalizer search;
 #original cells stay LOCKED, fence/spacing/PG/pin-distance/RC gates remain.
 text=(D/'io_protect.tcl').read_text();assert text.count('detailed_placement -max_displacement {10 10}')==1
 (D/'io_protect.tcl').write_text(text.replace('detailed_placement -max_displacement {10 10}','detailed_placement -max_displacement {50 10}'))
 (D/'IO_SEARCH.json').write_text(json.dumps(dict(horizontal_um=50,vertical_um=10,original_placement_locked=True,acceptance_rules_unchanged=True,reason='Actual166 three newBUF_X16 overlap/padding failures after10um search; no original placement may move'),indent=2)+'\n')
if a.buffer_locality:
 shutil.copyfile(Path(__file__).parent/'buffer_locality.tcl',D/'buffer_locality.tcl')
 with(D/'io_protect.tcl').open('a')as f:f.write('\nsource {'+str(D/'buffer_locality.tcl')+'}\n')
config=(S/'config.mk').read_text().replace(str(S),str(D))
# 20ps was a repair target, never an acceptance waiver. Stop padding paths
# already above the unchanged exact0ns final hold gate; original SDC is copied.
config=re.sub(r'^export HOLD_SLACK_MARGIN = .*$', 'export HOLD_SLACK_MARGIN = 0',config,flags=re.M)
config=re.sub(r'^export SETUP_SLACK_MARGIN = .*$', 'export SETUP_SLACK_MARGIN = 0.060',config,flags=re.M)
config+='\nexport PRE_GLOBAL_ROUTE_TCL = '+str(D/'io_protect.tcl')+'\n'
if a.path_evidence or a.measured_input_evidence:
 assert not(a.path_evidence and a.measured_input_evidence)
 diagnosis=a.path_evidence or a.measured_input_evidence
 evidence=json.loads((diagnosis/'receipt.json').read_text());assert evidence['passed']
 for f,h in evidence['inputs'].items():assert sha(Path(f))==h
 rows=[r.split('\t')for r in(diagnosis/'failing-paths.tsv').read_text().splitlines()]
 assert rows and all(r[0]in ['min','max']and float(r[3])<0 for r in rows)
 if a.measured_input_evidence:
  assert a.capacity==1024 and all('/r166_1024/base/'in f for f in evidence['inputs'])
  selected=[r for r in rows if r[0]=='min'and'/'not in r[1]]
  assert selected,'No measured failing external hold path'
 else:
  assert all(r[0]=='min'and'/'not in r[1]for r in rows),'Only measured external hold paths supported'
  selected=rows
 worst={}
 for r in selected:worst[r[1]]=min(worst.get(r[1],0),float(r[3]))
 assert len(worst)<=(32 if a.measured_input_evidence else 4) and all(s>-.1 for s in worst.values())
 (D/'EXTRACTED_PATH_BINDING.json').write_text(json.dumps({'diagnosis':str(diagnosis),'inputs':evidence['inputs'],'rows':rows,'selected_external_hold_rows':selected,'selected_ports':worst,'scope':'Only measured external inputs receive shared delay; all internal/setup failures remain mandatory and are not waived'},indent=2)+'\n')
 (D/'extra_input.tcl').write_text('set r166_extra_ports [dict create '+' '.join('{'+n+'} '+str(s)for n,s in worst.items())+']\n'+(Path(__file__).parent/'extra_input.tcl').read_text())
 with(D/'io_protect.tcl').open('a')as f:f.write('\nsource '+str(D/'extra_input.tcl')+'\n')
if a.endpoint_budget:
 import math
 assert a.capacity==1024 and a.buffer_locality,'Measured endpoint buffers require explicit physical ownership'
 budget=json.loads((a.endpoint_budget/'receipt.json').read_text());assert budget['passed']
 diagnosis=Path(budget['diagnosis']);dr=json.loads((diagnosis/'receipt.json').read_text())
 assert dr['passed']and dr['inputs']==budget['inputs']and sha(diagnosis/'receipt.json')==budget['diagnosis_receipt_sha256']and sha(diagnosis/'failing-paths.tsv')==budget['failing_paths_sha256']
 for name,digest in budget['inputs'].items():assert sha(Path(name))==digest
 rows=budget['rows'];assert rows and len(rows)<=1000
 delays={};headroom_limited=[]
 for row in rows:
  name=row['endpoint'];assert name.endswith('/D')and '{'not in name and '}'not in name and '\n'not in name and row['hold_ns']<0
  desired=max(1,math.ceil((0.040-row['hold_ns'])/0.025))
  #348's actual240026/D has only61.2ps setup headroom as well as-14ps hold.
  # Limit optional reserve there instead of blindly adding three delay cells.
  # These are planning estimates, never a cell-delay or final-STA guarantee.
  allowed=math.floor((row['setup_ns']-0.020)/0.040)
  minimum=max(1,math.ceil((-row['hold_ns']+0.005)/0.025))
  count=min(desired,allowed);assert minimum<=count<=8,('Insufficient measured setup headroom; redesign this endpoint',row,desired,allowed)
  assert row['setup_ns']>count*0.040+0.020
  if count<desired:headroom_limited.append(dict(endpoint=name,desired_cells=desired,planned_cells=count,actual_setup_ns=row['setup_ns'],actual_hold_ns=row['hold_ns']))
  assert name not in delays;delays[name]=count
 assert sum(delays.values())<=5000
 binding=dict(budget=str(a.endpoint_budget),budget_receipt_sha256=sha(a.endpoint_budget/'receipt.json'),diagnosis=str(diagnosis),inputs=budget['inputs'],rows=rows,endpoint_buffer_counts=delays,headroom_limited=headroom_limited,planning_hold_reserve_ns=0.040,planning_delay_per_cell_ns=0.025,scope='Only actual final SPEF hold-failing DFF data endpoints receive identity buffers. Optional optimization reserve is limited by measured maximum-path headroom; original SDC and final extracted timing/electrical/DRC gates remain mandatory.')
 (D/'EXTRACTED_ENDPOINT_BINDING.json').write_text(json.dumps(binding,indent=2)+'\n')
 (D/'extracted_endpoints.tcl').write_text('set r166_endpoint_delays [dict create '+' '.join('{'+n+'} '+str(c)for n,c in delays.items())+']\n'+(Path(__file__).parent/'extracted_endpoints.tcl').read_text())
 with(D/'io_protect.tcl').open('a')as f:f.write('\nsource {'+str(D/'extracted_endpoints.tcl')+'}\n')
if a.short_clock:
 shutil.copyfile(Path(__file__).parent/'short_clock.tcl',D/'short_clock.tcl')
 with(D/'io_protect.tcl').open('a')as f:f.write('\nsource '+str(D/'short_clock.tcl')+'\n')
if a.measured_grt_reserve:
 failure=a.measured_grt_reserve;receipt=json.loads((failure/'receipt.json').read_text());log=(failure/'flow.log').read_text()
 assert a.capacity==1024 and receipt['capacity']==1024 and receipt['exit']!=0
 assert '[ERROR GRT-0116] Global routing finished with congestion.'in log
 assert '[WARNING GRT-0704] Try reduce the layer adjustment from 25% to 12%'in log
 # This is the router's estimated upper-layer reserve, not a design rule.
 # Keep real obstructions, routing layers, original SDC, zero-overflow exit
 # and all final native/GDS/timing/electrical gates unchanged.
 if a.lower_reserve==0.3:assert 'metal2'in log and 'metal3'in log and ' / 294'in log,'Missing measured lower-layer congestion'
 script=D/'fastroute.tcl';script.write_text('set_global_routing_layer_adjustment metal2-metal3 '+str(a.lower_reserve)+'\nset_global_routing_layer_adjustment metal4-$::env(MAX_ROUTING_LAYER) 0.12\nset_routing_layers -clock $::env(MIN_CLK_ROUTING_LAYER)-$::env(MAX_ROUTING_LAYER)\nset_routing_layers -signal $::env(MIN_ROUTING_LAYER)-$::env(MAX_ROUTING_LAYER)\n')
 config+='\nexport FASTROUTE_TCL = '+str(script)+'\n'
 # The reused CTS DB already carries floorplan routing settings. Reapply
 # after loading that DB: FASTROUTE_TCL alone runs only at floorplan time.
 with(D/'io_protect.tcl').open('a')as hook:hook.write('\nsource {'+str(script)+'}\nputs {R166_UPPER_ROUTING_RESERVE=0.12; lower_reserve='+str(a.lower_reserve)+'; zero_overflow_required=1}\n')
 (D/'GRT_RESERVE_AUDIT.json').write_text(json.dumps({'failure_source':str(failure),'failure_receipt_sha256':sha(failure/'receipt.json'),'failure_log_sha256':sha(failure/'flow.log'),'source_config_sha256':sha(failure/'config.mk'),'original_upper_reserve':0.25,'new_upper_reserve':0.12,'original_lower_reserve':0.5,'lower_layer_reserve':a.lower_reserve,'congested_global_route_allowed':False,'scope':'Measured GRT-0704 upper reserve recommendation; lower .3 comparison only after measured M2/M3 overflow. Computational capacity estimate only, not a geometry/rule/acceptance change.'},indent=2)+'\n')
if a.grt_closure_evidence:
 assert a.capacity==1024 and a.buffer_locality
 prior=a.grt_closure_evidence;old=prior.parent.parent/'attempt132/physical'
 files=[prior/'flow/logs/nangate45/r166_1024/base/5_1_grt.json',prior/'flow/results/nangate45/r166_1024/base/5_1_grt.odb',old/'flow/logs/nangate45/r166_1024/base/5_1_grt.json',old/'flow/logs/nangate45/r166_1024/base/6_report.json']
 measured=json.loads(files[0].read_text());gm=json.loads(files[2].read_text());fm=json.loads(files[3].read_text())
 assert measured['globalroute__timing__drv__max_cap']>0 and measured['globalroute__timing__drv__hold_violation_count']>0
 setup_loss=gm['globalroute__timing__setup__ws']-fm['finish__timing__setup__ws'];hold_loss=gm['globalroute__timing__hold__ws']-fm['finish__timing__hold__ws']
 assert 0.100<setup_loss<0.120 and 0.030<hold_loss<0.045
 for f in files:before[str(f)]=sha(f)
 (D/'GRT_CLOSURE_EVIDENCE.json').write_text(json.dumps(dict(inputs={str(f):sha(f)for f in files},measured_setup_loss_ns=setup_loss,measured_hold_loss_ns=hold_loss,setup_target_ns=0.150,hold_target_ns=a.grt_hold_goal,maximum_rounds=6,acceptance_rules_unchanged=True,scope='179 actual post-DPL global RC violations; 132 measured GRT-to-RCX losses determine optimization targets. Final independent original gates still mandatory.'),indent=2)+'\n')
 shutil.copyfile(Path(__file__).parent/'grt_closure.tcl',D/'grt_closure.tcl')
 if a.grt_hold_goal==0:
  script=D/'grt_closure.tcl';script.write_text('set ::r166_grt_hold_goal 0.0\n'+script.read_text())
  evidence={}
  for attempt in [297,298]:
   prior_log=S.parent.parent/('attempt'+str(attempt))/'physical/flow.log'
   data=prior_log.read_bytes();assert b'$auto$ff.cc:337:slice$272340/D'in data
   snapshot=D/('GRT_GOAL_PRIOR'+str(attempt)+'.log');snapshot.write_bytes(data)
   evidence[str(prior_log)]=dict(observed_prefix_bytes=len(data),snapshot=snapshot.name,snapshot_sha256=sha(snapshot),scope='Immutable observation of a growing original log; no claim its later whole-file hash remains equal')
  (D/'GRT_EXACT_HOLD_GOAL.json').write_text(json.dumps(dict(optimization_goal_ns=0,prior_positive_goal_ns=0.060,observed_nonconvergent_logs=evidence,reason='Actual297/298 traverse thousands of positive-slack endpoints before a whole-pass iteration check. Stop padding positive hold paths; final independent extracted hold/setup must still be nonnegative and all counts zero. Final failures require new measured repair, never qualification.',reference='https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/rsz/src/RepairHold.cc',scope='Optimizer objective only; original SDC and exact final acceptance gates unchanged'),indent=2)+'\n')
 if a.hold_batch_iterations:
  prior_failures={}
  for attempt in [192,202]:
   failed=S.parent.parent/('attempt'+str(attempt))/'physical'
   assert json.loads((failed/'receipt.json').read_text())['exit']!=0
   text=(failed/'flow.log').read_text()
   assert '[ERROR RSZ-0060] Max buffer count reached.'in text
   assert '$auto$ff.cc:337:slice$272340/D'in text
   for file in [failed/'receipt.json',failed/'flow.log']:prior_failures[str(file)]=sha(file)
  (D/'repair-help.tcl').write_text('help repair_timing\n')
  with(D/'repair-help.log').open('w')as log:subprocess.run(['openroad','-no_init','-exit',str(D/'repair-help.tcl')],stdout=log,stderr=subprocess.STDOUT,check=True)
  assert '-max_iterations'in(D/'repair-help.log').read_text(),'Actual frozen tool does not advertise the requested iteration option'
  script=D/'grt_closure.tcl';script.write_text('set ::r166_hold_batch_iterations '+str(a.hold_batch_iterations)+'\n'+script.read_text())
 (D/'GRT_REPAIR_POLICY.json').write_text(json.dumps(dict(setup_optimization_goal_ns=0.150,hold_optimization_goal_ns=a.grt_hold_goal,hold_repair_setup_guard_ns=0,actual_round_checkpoints=True,final_acceptance_unchanged=True,reason='192/202 combined repair retained150ps setup optimization margin as the hold insertion guard; separate optimization phases while retaining exact final300MHz/nonnegative setup and hold/zero electrical gates'),indent=2)+'\n')
 if a.hold_batch_iterations:
  policy=D/'GRT_REPAIR_POLICY.json';record=json.loads(policy.read_text());record.update(hold_iterations_per_routed_batch=a.hold_batch_iterations,endpoint_operations_bounded=False,actual_help_sha256=sha(D/'repair-help.log'),failure_inputs=prior_failures,bounded_reason='192/202 actual RSZ-0060 after68374/68342 buffers at unchanged14ps endpoint. Historical outer-loop request only:297/298 showed a whole endpoint pass can exceed it. It does not bound endpoint operations or buffer count. Final gates unchanged.',reference='https://openroad.readthedocs.io/en/latest/main/src/rsz/README.html#repair-timing');policy.write_text(json.dumps(record,indent=2)+'\n')
 with(D/'io_protect.tcl').open('a')as hook:hook.write('\nsource {'+str(D/'grt_closure.tcl')+'}\n')
(D/'config.mk').write_text(config)
env=os.environ.copy();env.update(NUM_CORES='16',OMP_NUM_THREADS='16');commands=[];code=0
with(D/'flow.log').open('w')as log:
 for target in ['do-5_1_grt','do-5_2_route','do-5_3_fillcell','do-5_route','do-5_route.sdc','do-6_1_fill','do-6_1_fill.sdc','do-6_report']:
  cmd=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(D/'config.mk'),'WORK_HOME='+str(D/'flow'),target];commands.append(cmd);v=subprocess.run(cmd,env=env,stdout=log,stderr=subprocess.STDOUT)
  if v.returncode:code=v.returncode;break
assert before=={f:sha(Path(f))for f in before}
(D/'receipt.json').write_text(json.dumps({'capacity':a.capacity,'exit':code,('source_final'if a.from_final else'source_cts'):str(S),'source_unchanged':True,'source_hashes':before,'commands':commands,'qualification_transferred':False,'passed':False,'acceptance_sdc_unchanged':sha(S/'input.sdc')==sha(D/'input.sdc'),'change':'Source-bound finite IO/endpoint repair and real global RC closure. Original300MHz/IO and every exact final nonnegative/zero-violation gate unchanged; optimizer goals are recorded separately.'},indent=2)+'\n');raise SystemExit(code)
