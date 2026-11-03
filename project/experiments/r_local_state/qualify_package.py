"""Receive only successful exact-source final gates, then package real native views."""
from pathlib import Path
import argparse,hashlib,json,subprocess,os,shutil,tarfile,csv
p=argparse.ArgumentParser()
for n in ['physical','evaluation','functional','geometry','mapped','mapping-proof']:p.add_argument('--'+n,type=Path,required=True)
p.add_argument('--capacity',type=int,choices=[256,1024],required=True);a=p.parse_args()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(p.read_text())
P=Path(__file__).resolve().parent;R=a.physical/'flow/results/nangate45'/('r166_'+str(a.capacity))/'base'
O=Path.cwd()/'delivery';O.mkdir(exist_ok=False);checks={};evidence={};clock_proofs=set();incremental_proofs=set()
def receive(path):
 obj=read(path);evidence[str(path)]=sha(path);return obj
e=receive(a.evaluation/'receipt.json');f=receive(a.functional/'receipt.json');g=receive(a.geometry/'GEOMETRY.json')[0];m=receive(a.mapped/'receipt.json')
checks['complete_physical']=e['passed']is True and e['capacity']==a.capacity and e['physical']==str(a.physical)and bool(e['checks'])and all(e['checks'].values())
checks['exact_final_function']=f['passed']is True and f['capacity']==a.capacity and f['inputs'][str(R/'6_final.v')]==sha(R/'6_final.v')
checks['complete_3_by_63_and_protocol']=len(f['tasks'])==192 and all(r['passed']is True for r in f['tasks']) and all({r['case']for r in f['tasks']if r['initialization']==i}==set(range(-1,63))for i in range(3))
checks['exact_geometry']=g['def_sha256']==sha(R/'6_final.def')and g['spef_sha256']==sha(R/'6_final.spef')and g['all_selection_tree_nets_extracted']and g['centerline_matches_router_within_2um_each_layer']and all(s['exit']==0 for s in g['stages'])
proof=receive(a.mapping_proof/'receipt.json')
checks['complete_mapping_formal']=proof['passed']is True and proof['proof']['passed']is True and proof['mapped']==str(a.mapped)and proof['inputs'][str(a.mapped/'mapped.json')]==sha(a.mapped/'mapped.json')and proof['source_sha256']==m['source_sha256']
for path,digest in proof['inputs'].items():assert sha(Path(path))==digest
checks['mapped_structure']=m['passed']is True and m['mapped_json_sha256']==sha(a.mapped/'mapped.json')
for path,row in e['artifacts'].items():assert sha(Path(path))==row['sha256']
for path,digest in f['inputs'].items():assert sha(Path(path))==digest
lineage=[];q=a.physical;seen=set();grt_sources=set()
while True:
 assert q not in seen;seen.add(q);v=receive(q/'receipt.json');assert v.get('exit')==0 or q!=a.physical
 lineage.append({'physical':str(q),'receipt_sha256':sha(q/'receipt.json')})
 for path,digest in v.get('source_hashes',{}).items():assert sha(Path(path))==digest
 if 'source_grt'in v:
  resume=receive(q/'GRT_RESUME.json');s=Path(v['source_grt'])
  assert resume['source']==str(s)and resume['qualification_transferred']is False and resume['checkpoint']==str(s/'flow/results/nangate45/r166_1024/base/5_1_grt.odb')and sha(Path(resume['checkpoint']))==resume['checkpoint_sha256']
  assert resume['inputs']==v['source_hashes']and sha(Path(resume['metrics']))==resume['metrics_sha256']
  gm=read(Path(resume['metrics']));assert gm['globalroute__timing__setup__ws']>=0 and gm['globalroute__timing__hold__ws']>=0
  assert all(gm['globalroute__timing__drv__'+k]==0 for k in ['setup_violation_count','hold_violation_count','max_cap','max_slew'])
  rp=Path(resume['probe']);pr=receive(rp/'receipt.json');assert pr['passed']and pr['physical']==str(s)and pr['qualification']is False and sha(rp/'receipt.json')==resume['probe_receipt_sha256']and pr['inputs'][resume['checkpoint']]==resume['checkpoint_sha256']
  for name,digest in pr['inputs'].items():assert sha(Path(name))==digest
  grt_sources.add(s);checks['source_bound_grt_stage_resume']=True
  if 'pg_data_placement'in resume:
   from pg_data_placement import verify_final
   assert resume['post_eco_grt_timing_qualified']is False and resume['pg_data_placement']==str(q/'PG_DATA_PLACEMENT.json')and sha(q/'PG_DATA_PLACEMENT.json')==resume['pg_data_placement_sha256']
   verify_final(q,q/'flow/results/nangate45/r166_1024/base/6_final.def');checks['measured_data_only_pg_placement']=True
 sources=[v[k]for k in ['source_cts','source_placed','source_gpl','source_final','source_grt']if k in v]
 if not sources:
  checks['mapped_lineage']=v['mapped_json_sha256']==m['mapped_json_sha256']and v['source_sha256']==m['source_sha256'];break
 assert len(sources)==1;q=Path(sources[0])
checks['original_acceptance_sdc']=sha(a.physical/'input.sdc')==sha(P/'physical.sdc')
for row in lineage:
 src=Path(row['physical']);file=src/'CLOCK_ROUTE_BINDING.json'
 local=src/'LOCAL_SHORT_ROUTE_BINDING.json'
 if local.exists():
  lr=receive(local);assert lr['qualification_transferred']is False and lr['temporary_obstructions_only']is True
  for name,digest in lr['inputs'].items():assert sha(Path(name))==digest
  diagnosis=Path(lr['diagnosis']);dr=receive(diagnosis/'receipt.json')
  assert sha(diagnosis/'receipt.json')==lr['diagnosis_receipt_sha256']and dr['passed']is False and dr['no_marker_or_rule_exclusions']and dr['native_drc_count']==len(lr['shorts'])
  parent=Path(receive(src/'FINAL_RESUME.json')['source_final'])
  assert dr['original_odb_sha256']==sha(parent/'flow/results/nangate45/r166_1024/base/6_final.odb')and dr['native_report_sha256']==sha(diagnosis/'complete.rpt')
  classes={r[0]:r[1]for r in [line.split('\t')for line in(src/'SHORT_NET_CLASSES.tsv').read_text().splitlines()]}
  data=set((src/'SHORT_DATA_NETS.tsv').read_text().splitlines());expected=set()
  for first,second,*unused in lr['shorts']:
   assert {classes[first],classes[second]}=={'CLOCK','SIGNAL'}
   expected.update(n for n in [first,second]if classes[n]=='SIGNAL')
  assert data==expected and data
  removed=(src/'SHORT_TEMP_OBSTRUCTIONS_REMOVED.tsv').read_text().split();assert len(removed)==3 and int(removed[0])==len(lr['shorts'])and removed[1]==removed[2]
  assert len((src/'SHORT_TEMP_OBSTRUCTIONS.tsv').read_text().splitlines())==len(lr['shorts'])
  checks['source_bound_native_short_reroute']=True
 inc=src/'INCREMENTAL_ROUTE_BINDING.json'
 if inc.exists():
  ir=receive(inc);assert ir['qualification_transferred']is False
  for name,digest in ir['inputs'].items():assert sha(Path(name))==digest
  nr=Path(ir['noop_probe']);np=receive(nr/'receipt.json');assert np['passed']and np['whole_native_def_bytes_identical']and np['qualification']is False and sha(nr/'receipt.json')==ir['noop_receipt_sha256']
  ia=receive(src/'INCREMENTAL_ROUTE_AUDIT.json');assert ia['passed']and not ia['changed_untouched_nets']and sha(src/'INCREMENTAL_ROUTE_AUDIT.json')==ir['audit_sha256']
  assert ia['before_def_sha256']==sha(src/'INCREMENTAL_BEFORE.def')and ia['after_def_sha256']==sha(src/'INCREMENTAL_AFTER_GRT.def')and ia['affected_inventory_sha256']==sha(src/'INCREMENTAL_AFFECTED_NETS.tsv')
  checks['finite_incremental_route_source']=True
  if(src/'PG_DATA_PLACEMENT.json').exists():
   from pg_data_placement import verify_final
   plan=verify_final(src,src/'flow/results/nangate45/r166_1024/base/6_final.def');assert plan['pre_route_incremental_checkpoint']
   checks['measured_incremental_pg_placement']=True
 if not file.exists():continue
 binding=receive(file);assert binding['qualification_transferred']is False
 continued=src/'CONTINUED_CLOCK_PREPARE.json'
 if continued.exists():
  cp=receive(continued);assert cp['qualification_transferred']is False and cp['audit_producer_sha256']==sha(P/'fixed_clock_routes.py')and cp['fixed_overlay_sha256']==sha(src/'CLOCK_FIXED.def')and cp['routed_overlay_sha256']==sha(src/'CLOCK_ROUTED.def')
  for name,digest in cp['inputs'].items():assert sha(Path(name))==digest
  if src not in grt_sources:
   pg=receive(src/'PG_PRE_ROUTE.json');assert pg['passed']and pg['checkpoint_sha256']==sha(Path(pg['checkpoint']))and pg['native_tsv_sha256']==sha(src/'PG_PRE_ROUTE.tsv')
  checks['continued_fixed_clock_source']=True
 proof=Path(binding['proof']);assert proof.parent.parent==a.physical.parent.parent
 pr=receive(proof/'receipt.json');assert pr['passed']and sha(proof/'receipt.json')==binding['proof_receipt_sha256']and pr['source_odb_sha256']==binding['source_odb_sha256']==sha(Path(binding['source_odb']))
 for name,item in pr['artifacts'].items():assert sha(proof/name)==item['sha256']and(proof/name).stat().st_size==item['bytes']
 assert sha(src/'CLOCK_BASELINE.json.gz')==binding['baseline_sha256']and sha(src/'CLOCK_FIXED.def')==binding['overlay_sha256']
 if src in grt_sources:
  # This ancestor failed before DRT. Its exact successful GRT stage is an
  # input, never a qualified macro. The newly produced final leaf above must
  # pass its own strict restoration and all three complete geometry audits.
  assert src!=a.physical;clock_proofs.add(proof);continue
 assert binding['restoration_protocol']=='exact-source-clock-restore-v1'
 restored=receive(src/'CLOCK_RESTORE_PRECHECK.json')
 assert restored['passed']and restored['protocol']==binding['restoration_protocol']and restored['binding_sha256']==sha(file)and restored['def_sha256']==sha(src/'CLOCK_pre-restore.def')and restored['producer_sha256']==sha(P/'fixed_clock_routes.py')and restored['baseline_sha256']==binding['baseline_sha256']and restored['overlay_sha256']==binding['overlay_sha256']
 assert restored['clock_nets']==binding['clock_nets']==restored['fully_absent_routes']+restored['exact_surviving_routes']and restored['clock_cells']==binding['clock_cells']
 for phase in ['before-detail','after-detail','final']:
  audit=receive(src/('CLOCK_AUDIT_'+phase+'.json'))
  expected=src/('CLOCK_'+phase+'.def')if phase!='final'else src/'flow/results/nangate45/r166_1024/base/6_final.def'
  assert audit['passed']and audit['phase']==phase and audit['binding_sha256']==sha(file)and audit['def_sha256']==sha(expected)and audit['baseline_sha256']==binding['baseline_sha256']and audit['producer_sha256']==sha(P/'fixed_clock_routes.py')
 clock_proofs.add(proof);checks['preserved_clock_routes']=True
checks['source_files_present']=bool(m['source_sha256'])
for path,digest in m['source_sha256'].items():
 actual=P.parent.parent/'rtl/r_local_state'/Path(path).name
 assert actual.is_file()and sha(actual)==digest,'Packaged RTL differs from proved mapped source'
result={'passed':all(checks.values()),'capacity':a.capacity,'checks':checks,'evidence':evidence,'lineage':lineage,'frequency_mhz':300,'state_bytes':a.capacity*8,'state_versions':2,'lanes':8,'read_storage_edges':'E0 request,E1 select,E2 local data,E3 merge,E4 external enqueue','native_leaf_qualified':all(checks.values()),'hierarchical_lib_timing_qualified':False,'m11_m12_system_qualified':False,'scope':'Exact standalone local-state R macro. Native final physical acceptance only; no system or old ISA substitution claim.'}
result['finalize_pipeline']=bool(m.get('finalize_pipeline',0))
result['op4_op5_extra_cycles']=int(result['finalize_pipeline'])
(O/'QUALIFICATION.json').write_text(json.dumps(result,indent=2)+'\n');assert result['passed'],checks
for sub in ['native','abstract','evidence','source','meta']:(O/sub).mkdir()
with(O/'meta/CASE_CYCLES.csv').open('w',newline='')as stream:
 writer=csv.writer(stream);writer.writerow(['initialization','case','mode','elements','layers','tokens','checks','cycles','logical_time_us_at_300MHz'])
 for row in sorted(f['tasks'],key=lambda r:(r['initialization'],r['case'])):
  if row['case']<0:continue
  case=row['corpus'];score=row['result'];cycles=score['cycles']
  writer.writerow([row['initialization'],row['case'],case['mode'],case['elements'],case['layers'],case['tokens'],score['checks'],cycles,cycles/300.0])
summary=f'''# R local-state {a.capacity}: exact standalone native macro

Two state versions, {a.capacity*8} state bytes total, eight arithmetic lanes.
Ordinary standard-cell storage; not a foundry SRAM macro.
Optional finalization pipeline: {result['finalize_pipeline']}; op4/op5 extra cycles: {result['op4_op5_extra_cycles']}.
Original 300MHz / I/O SDC, fixed internal M1–M10, 821 internal M10 signal pins.

Final extracted setup: {e['metrics']['finish__timing__setup__ws']} ns.
Final extracted hold: {e['metrics']['finish__timing__hold__ws']} ns.
All required physical checks passed; complete original GDS items: {e['full_deck_items']}.
Exact final cell netlist: 189 numeric cases and three protocol tests passed.
Actual final-cell cycle counts are in meta/CASE_CYCLES.csv; time is cycles/300MHz,
not a full-model, power or system performance measurement.

Native files are in native/; actual-source abstract views are in abstract/.
Evidence, source and lineage are preserved with per-member MANIFEST hashes.
No old-ISA substitution, hierarchical timing-model or M11/M12 system qualification.
'''
(O/'MEASURED_SUMMARY.md').write_text(summary)
files={}
for suffix in ['v','sdc','def','odb','spef','gds']:
 src=R/('6_final.'+suffix);assert src.is_file()and src.stat().st_size>0;dest=O/'native'/src.name;shutil.copyfile(src,dest);files[src.name]={'sha256':sha(dest),'bytes':dest.stat().st_size}
for name in ['r_stream_local.lef','r_stream_local_typ.lib']:shutil.copyfile(R/name,O/'abstract'/name)
# Render the actual accepted GDS, preserving every layer; a picture is not DRC evidence.
script="import pya\nv=pya.LayoutView()\nv.load_layout("+repr(str(O/'native/6_final.gds'))+",0)\nv.max_hier()\nv.add_missing_layers()\nv.zoom_fit()\nv.save_image("+repr(str(O/'native/layout.png'))+",1600,1600)\n"
(O/'meta/render.py').write_text(script)
with(O/'meta/render.log').open('w')as log:subprocess.run(['env','QT_QPA_PLATFORM=offscreen','klayout','-z','-r',str(O/'meta/render.py')],stdout=log,stderr=subprocess.STDOUT,check=True)
assert(O/'native/layout.png').stat().st_size>1000
shutil.copytree(a.evaluation,O/'evidence/physical')
shutil.copytree(a.functional,O/'evidence/final-function')
shutil.copytree(a.geometry,O/'evidence/geometry')
shutil.copytree(a.mapping_proof,O/'evidence/mapping-formal')
shutil.copyfile(a.mapped/'receipt.json',O/'evidence/mapped-receipt.json')
shutil.copyfile(a.mapped/'SELECTION.json',O/'evidence/mapped-selection.json')
for name in ['map.ys','abc.constr','abc-help.log']:
 if(a.mapped/name).exists():shutil.copyfile(a.mapped/name,O/'evidence'/('mapped-'+name))
shutil.copytree(P.parent.parent/'rtl/r_local_state',O/'source/rtl')
shutil.copytree(P,O/'source/runners')
for i,row in enumerate(lineage):
 src=Path(row['physical']);d=O/'meta'/('lineage%02d'%i);d.mkdir()
 for name in ['LOCAL_SHORT_ROUTE_BINDING.json','SHORT_NET_CLASSES.tsv','SHORT_DATA_NETS.tsv','SHORT_TEMP_OBSTRUCTIONS.tsv','SHORT_TEMP_OBSTRUCTIONS_REMOVED.tsv']:
  if(src/name).exists():shutil.copyfile(src/name,d/name)
 for name in ['INCREMENTAL_ROUTE_BINDING.json','INCREMENTAL_ROUTE_AUDIT.json','INCREMENTAL_BEFORE.def','INCREMENTAL_AFTER_GRT.def','INCREMENTAL_AFFECTED_NETS.tsv','FINAL_DATA_ROUTE_RETENTION.json','incremental.tcl']:
  if(src/name).exists():shutil.copyfile(src/name,d/name)
 if(src/'INCREMENTAL_ROUTE_BINDING.json').exists():
  ir=read(src/'INCREMENTAL_ROUTE_BINDING.json');nr=Path(ir['noop_probe']);assert nr.parent.parent==a.physical.parent.parent;incremental_proofs.add(nr)
 for name in ['CONTINUED_CLOCK_PREPARE.json','CLOCK_ROUTED.def','PG_PRE_ROUTE.tsv','PG_PRE_ROUTE.json']:
  if(src/name).exists():shutil.copyfile(src/name,d/name)
 for name in ['PG_DATA_PLACEMENT.json','pg_data_placement.tcl']:
  if(src/name).exists():shutil.copyfile(src/name,d/name)
 if(src/'PG_DATA_PLACEMENT.json').exists():
  pg=read(src/'PG_DATA_PLACEMENT.json')
  if pg.get('rerouted_data_nets'):
   probe=Path(pg['probe']);raw=read(probe/'receipt.json')
   (d/'PG_ROUTE_SCOPE_NOTE.json').write_text(json.dumps(dict(original_probe_receipt_sha256=sha(probe/'receipt.json'),actual_probe_script_sha256=sha(probe/'probe.tcl'),rerouted_data_nets=raw['rerouted_data_nets'],scope='Raw historical receipt retained unchanged. Its generic incident-route prose was incomplete: the explicit rerouted_data_nets field and actual Tcl also remove these native-measured colliding data wires. No original clock or unrelated data route is removed by that probe. This is component evidence, not final physical qualification.'),indent=2)+'\n')
 for name in ['CLOCK_ROUTE_BINDING.json','CLOCK_BASELINE.json.gz','CLOCK_FIXED.def','CLOCK_LOCKED_CELLS.tsv','CLOCK_NATIVE_NAMES.tsv','clock_source_names.log','CLOCK_RESTORE_PRECHECK.json','CLOCK_pre-restore.def','CLOCK_before-detail.def','CLOCK_after-detail.def','CLOCK_AUDIT_before-detail.json','CLOCK_AUDIT_after-detail.json','CLOCK_AUDIT_final.json']:
  if(src/name).exists():shutil.copyfile(src/name,d/name)
 if(src/'GRT_EXACT_HOLD_GOAL.json').exists():
  goal=read(src/'GRT_EXACT_HOLD_GOAL.json');shutil.copyfile(src/'GRT_EXACT_HOLD_GOAL.json',d/'GRT_EXACT_HOLD_GOAL.json')
  for observed in goal['observed_nonconvergent_logs'].values():
   snapshot=src/observed['snapshot'];assert sha(snapshot)==observed['snapshot_sha256']and snapshot.stat().st_size==observed['observed_prefix_bytes']
   shutil.copyfile(snapshot,d/snapshot.name)
 for name in ['receipt.json','config.mk','input.sdc','regions.json','GRT_RESUME.json','HOLD_ENDPOINT_ECO.tsv','INPUT_HOLD_AUDIT.tsv','PORT_BUFFER_AUDIT.tsv','IO_SEARCH.json','BUFFER_LOCALITY.tsv','BUFFER_REPAIR_GUARD.tsv','GRT_CLOSURE_EVIDENCE.json','GRT_CLOSURE.tsv','buffer_locality.tcl','EXTRACTED_PATH_BINDING.json','EXTRACTED_INPUT_ECO.tsv','EXTRACTED_ENDPOINT_BINDING.json','EXTRACTED_ENDPOINT_ECO.tsv','CLOCK_ROOT_AUDIT.tsv','GRT_RESERVE_AUDIT.json','fastroute.tcl']:
  if(src/name).exists():shutil.copyfile(src/name,d/name)
 for name in ['FILES.sha256','run.sbatch','source-check.log']:
  if(src.parent/name).exists():shutil.copyfile(src.parent/name,d/name)
 # Preserve the actual generated hooks, including command units, alongside
 # the immutable historical receipts rather than silently rewriting them.
 for hook in src.glob('*.tcl'):shutil.copyfile(hook,d/hook.name)
 if(src/'FINAL_RESUME.json').exists():
  resume=read(src/'FINAL_RESUME.json');assert resume['qualification_transferred']is False
  for name,digest in resume['source_final_hashes'].items():assert sha(Path(name))==digest
  shutil.copyfile(src/'FINAL_RESUME.json',d/'FINAL_RESUME.json')
 if(src/'GRT_REPAIR_POLICY.json').exists():
  shutil.copyfile(src/'GRT_REPAIR_POLICY.json',d/'GRT_REPAIR_POLICY.json')
  policy=read(src/'GRT_REPAIR_POLICY.json')
  if policy.get('hold_iterations_per_routed_batch'):
   assert sha(src/'repair-help.log')==policy['actual_help_sha256']
   shutil.copyfile(src/'repair-help.log',d/'repair-help.log')
   for file,digest in policy['failure_inputs'].items():assert sha(Path(file))==digest
 if(src/'IO_SEARCH.json').exists():
  original=read(src/'IO_SEARCH.json')
  if 'horizontal_sites'in original:
   hook=src/'io_protect.tcl';assert 'detailed_placement -max_displacement {50 10}'in hook.read_text()
   (d/'IO_SEARCH_UNITS_CORRECTION.json').write_text(json.dumps(dict(horizontal_um=50,vertical_um=10,historical_receipt_sha256=sha(src/'IO_SEARCH.json'),actual_generated_hook_sha256=sha(hook),scope='Original174 CLI/JSON labels said sites/rows incorrectly. The unchanged OpenROAD command accepts microns. Raw receipt retained; no geometry, constraint or qualification change.'),indent=2)+'\n')
# Preserve the actual frozen runner/RTL source, not merely today's package code.
base=a.physical.parent.parent
attempts={Path(row['physical']).parent for row in lineage}|{a.evaluation.parent,a.functional.parent,a.geometry.parent,a.mapping_proof.parent,a.mapped.parents[1],Path.cwd()}
for row in lineage:
 src=Path(row['physical']);local=src/'LOCAL_SHORT_ROUTE_BINDING.json'
 if local.exists():
  diagnosis=Path(read(local)['diagnosis']);assert diagnosis.parent.parent==base;attempts.add(diagnosis.parent)
  target=O/'evidence'/('native-short-diagnosis-'+diagnosis.parent.name);target.mkdir()
  for name in ['receipt.json','complete.rpt','complete.tcl','complete.log','CHECKER_IDENTITY.json','CHECKER_BUILD_RECEIPT.json','CHECKER_UPSTREAM_SOURCES.json','CHECKER_SOURCE_RECHECK.json','INTERCHANGE_RECEIPT.json']:
   shutil.copyfile(diagnosis/name,target/name)
for proof in clock_proofs:
 attempts.add(proof.parent)
 shutil.copytree(proof,O/'evidence'/('clock-route-'+proof.parent.name))
for proof in incremental_proofs:
 attempts.add(proof.parent)
 shutil.copytree(proof,O/'evidence'/('incremental-noop-'+proof.parent.name))
for row in lineage:
 resume_file=Path(row['physical'])/'GRT_RESUME.json'
 if resume_file.exists():
  resume=read(resume_file);probe=Path(resume['probe']);assert probe.parent.parent==base
  attempts.add(probe.parent);shutil.copytree(probe,O/'evidence'/('grt-clock-restoration-'+probe.parent.name))
 pg_file=Path(row['physical'])/'PG_DATA_PLACEMENT.json'
 if pg_file.exists():
  pg=read(pg_file);probe=Path(pg['probe']);assert probe.parent.parent==base
  attempts.add(probe.parent);shutil.copytree(probe,O/'evidence'/('pg-data-placement-'+probe.parent.name))
  reroute=read(probe/'receipt.json').get('reroute_evidence')
  if reroute:
   er=Path(reroute);assert er.parent.parent==base
   attempts.add(er.parent);shutil.copytree(er,O/'evidence'/('pg-wire-collision-'+er.parent.name))
  diagnosis=Path(read(probe/'receipt.json')['diagnosis']);assert diagnosis.parent.parent==base
  attempts.add(diagnosis.parent);shutil.copytree(diagnosis,O/'evidence'/('pg-collision-'+diagnosis.parent.name))
  failed=Path(read(probe/'receipt.json')['physical']);assert failed.parent.parent==base
  attempts.add(failed.parent);rejected=O/'evidence'/('pg-rejected-'+failed.parent.name);rejected.mkdir()
  failed_names=['receipt.json','flow.log','CLOCK_ROUTE_BINDING.json']
  if pg.get('pre_route_incremental_checkpoint'):failed_names+=['PG_PRE_ROUTE.json','PG_PRE_ROUTE.tsv','INCREMENTAL_ROUTE_BINDING.json','INCREMENTAL_ROUTE_AUDIT.json','EXTRACTED_ENDPOINT_BINDING.json','FINAL_RESUME.json']
  else:failed_names+=['GRT_RESUME.json']
  for name in failed_names:shutil.copyfile(failed/name,rejected/name)
 policy_file=Path(row['physical'])/'GRT_REPAIR_POLICY.json'
 if policy_file.exists():
  for file,digest in read(policy_file).get('failure_inputs',{}).items():
   path=Path(file);assert sha(path)==digest and path.parents[2]==base
   attempts.add(path.parents[1])
 binding_file=Path(row['physical'])/'EXTRACTED_PATH_BINDING.json'
 if binding_file.exists():
  binding=read(binding_file);diagnosis=Path(binding['diagnosis']);assert diagnosis.parent.parent==base
  diagnostic=read(diagnosis/'receipt.json');assert diagnostic['passed']and diagnostic['inputs']==binding['inputs']
  for name,digest in diagnostic['inputs'].items():assert sha(Path(name))==digest
  attempts.add(diagnosis.parent)
  shutil.copytree(diagnosis,O/'evidence'/('input-path-'+diagnosis.parent.name))
 endpoint_file=Path(row['physical'])/'EXTRACTED_ENDPOINT_BINDING.json'
 if endpoint_file.exists():
  binding=read(endpoint_file);budget=Path(binding['budget']);diagnosis=Path(binding['diagnosis'])
  assert budget.parent.parent==base and diagnosis.parent.parent==base
  br=read(budget/'receipt.json');dr=read(diagnosis/'receipt.json')
  assert br['passed']and dr['passed']and sha(budget/'receipt.json')==binding['budget_receipt_sha256']and br['inputs']==dr['inputs']==binding['inputs']and br['rows']==binding['rows']
  assert sha(diagnosis/'receipt.json')==br['diagnosis_receipt_sha256']and sha(diagnosis/'failing-paths.tsv')==br['failing_paths_sha256']
  for name,digest in binding['inputs'].items():assert sha(Path(name))==digest
  attempts.update([budget.parent,diagnosis.parent])
  shutil.copytree(budget,O/'evidence'/('endpoint-headroom-'+budget.parent.name))
  shutil.copytree(diagnosis,O/'evidence'/('endpoint-path-'+diagnosis.parent.name))
if e.get('source_receiver'):attempts.add(Path(e['source_receiver']).parent)
if e.get('complete_native'):attempts.add(Path(e['complete_native']['source']).parent)
if e.get('complete_native',{}).get('checker',{}):
 tool=e['complete_native']['checker']
 if tool['kind']=='pinned-unmodified-upstream':
  build=read(a.evaluation/'complete-native/CHECKER_BUILD_RECEIPT.json')
  assert build['passed']and build['binary_sha256']==tool['binary_sha256']
  build_attempt=Path(build['build_attempt']);assert build_attempt.parent==base
  attempts.add(build_attempt)
binding=read(a.functional/'BUILD_BINDING.json');attempts.add(Path(binding['source_test']).parent)
for row in f.get('worker_sources',[]):
 attempt=Path(row['attempt']);assert attempt.parent==base
 assert sha(attempt/'run.sbatch')==row['run_sbatch_sha256']and sha(attempt/'FILES.sha256')==row['files_sha256']
 attempts.add(attempt)
needed_source_sets=set()
for attempt in attempts:
 index=attempt/'FILES.sha256';assert index.is_file()
 needed_source_sets.add(frozenset(line.split(None,1)[1].lstrip('*')for line in index.read_text().splitlines()if line.strip()))
archives={}
for archive in sorted(base.glob('source*.tar')):
 with tarfile.open(archive)as t:
  entries=[entry for entry in t.getmembers()if entry.isfile()]
  #Only actual frozen source scopes can be candidates. Do not hash unrelated
  #reference files in an unused broad repository archive. Exact member SHA
  #matching and every actual source-file verification below remain mandatory.
  if frozenset(entry.name for entry in entries)not in needed_source_sets:continue
  members={entry.name:hashlib.sha256(t.extractfile(entry).read()).hexdigest()for entry in entries}
  archives[archive.name]={'file_sha256':members,'git_archive_commit':t.pax_headers.get('comment'),'archive_sha256':sha(archive)}
(O/'source/archives').mkdir();source_index=[]
(O/'meta/frozen-attempts').mkdir()
for attempt in sorted(attempts):
 assert attempt.parent==base,'Foreign task source directory rejected'
 index=attempt/'FILES.sha256';assert index.is_file()
 actual={line.split(None,1)[1].lstrip('*'):line.split(None,1)[0]for line in index.read_text().splitlines()if line.strip()}
 matches=[name for name,row in archives.items()if row['file_sha256']==actual];assert matches,(str(attempt),'No exact frozen source archive')
 for name,expected in actual.items():assert sha(attempt/name)==expected
 chosen=matches[0];dest=O/'source/archives'/chosen
 if not dest.exists():shutil.copyfile(base/chosen,dest)
 meta=O/'meta/frozen-attempts'/attempt.name;meta.mkdir();metadata={}
 for file in sorted({attempt/n for n in ['FILES.sha256','run.sbatch','SUBMISSION.json','source-check.log']}|set(attempt.glob('source-check-*.log'))):
  if file.is_file():shutil.copyfile(file,meta/file.name);metadata[file.name]=sha(file)
 source_index.append({'attempt':str(attempt),'files_sha256':sha(index),'matching_archive':chosen,'archive_sha256':sha(dest),'matching_git_commit':archives[chosen]['git_archive_commit'],'all_exact_content_archive_matches':matches,'frozen_job_metadata':metadata})
(O/'meta/FROZEN_SOURCE_INDEX.json').write_text(json.dumps(source_index,indent=2)+'\n')
(O/'meta/SIX_FILES.json').write_text(json.dumps(files,indent=2)+'\n')
manifest={str(f.relative_to(O)):{'sha256':sha(f),'bytes':f.stat().st_size}for f in O.rglob('*')if f.is_file()}
(O/'MANIFEST.json').write_text(json.dumps(manifest,indent=2)+'\n')
archive=O.parent/('R-local-state-%d-300MHz.tar.gz'%a.capacity)
with tarfile.open(archive,'w:gz')as t:t.add(O,arcname='R-local-state-'+str(a.capacity))
(O.parent/'DELIVERY_RECEIPT.json').write_text(json.dumps({'passed':True,'archive':str(archive),'sha256':sha(archive),'bytes':archive.stat().st_size,'members':len(manifest)+1,'six_files':files,'scope':'Server bundle only; local download/hash/member reception remains separate'},indent=2)+'\n')
