"""Strict same-source C43 final aggregation. Run in ORFS container only after all gates finish."""
from pathlib import Path
import json,hashlib,re,sys,shutil,os,xml.etree.ElementTree as ET
R=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');run=R/'cu/runs/C-v43-margin-plan0';res=run/'flow/results/nangate45/c-overlay-current/base';a=R/'audit/C-v43-independent-v1'/run.name;p=R/'audit/C-final-v1'/run.name;m=R/'audit/C-final-v1'/('model-'+run.name);f=R/'audit'/('full-'+run.name);q=R/'audit/C43-plan0-final-proof'
cache={};evidence={}
def sha(path):
 path=Path(path).resolve()
 if path not in cache:
  h=hashlib.sha256()
  with path.open('rb') as z:
   for b in iter(lambda:z.read(4194304),b''):h.update(b)
  cache[path]=h.hexdigest()
 return cache[path]
def obj(path):
 path=Path(path);evidence[str(path.resolve())]=sha(path);return json.loads(path.read_text())
def hashes(d):
 for path,h in d.items():assert sha(path)==h,('Changed bound input',path)
def manifest(path):
 path=Path(path);d={}
 for row in path.read_text().splitlines():
  h,n=row.split(None,1);n=n.lstrip('*');z=Path(n);z=z if z.is_absolute() else path.parent/z;assert re.fullmatch('[a-f0-9]{64}',h);assert sha(z)==h,('Manifest mismatch',str(z));d[str(z.resolve())]=h
 evidence[str(path)]=sha(path);return d
def bound_receipt(path):
 d=obj(path)
 for key in ('hashes','sha256','source_sha256','inputs_sha256','input_hashes','transitive_sha256'):
  if key in d:hashes(d[key])
 return d
frozen=obj(a/'frozen-source.json');hashes(frozen['files_sha256']);assert frozen['run']==str(run)
manifest(run/'candidate.sha256');manifest(run/'inputs.sha256');manifest(run/'prepared.sha256')
before=obj(p/'inputs-before.json');assert before==obj(p/'inputs-after.json');hashes(before);manifest(p/'checker-scripts.sha256')
ind=bound_receipt(p/'independent-gates.json');assert ind['passed'] and ind['final_netlist_byte_equal_saved'] and ind['signal_die_macro_geometry_exact']
counts={k:int(v) for k,v in (s.split() for s in (p/'counts.tsv').read_text().splitlines())};assert set(counts)=={'setup','hold','capacitance','slew','fanout'} and not any(counts.values())
slacks={k:float(re.search(r'worst slack (?:max|min)\s+([-+0-9.eE]+)',(p/(k+'.rpt')).read_text())[1]) for k in ('setup','hold')};assert min(slacks.values())>=0 and slacks==ind['slacks_ns']
for name in ('async.rpt','electrical.rpt'):assert 'VIOLATED' not in (p/name).read_text().upper()
lines=lambda z:[s.strip() for s in z.read_text().splitlines() if s.strip() and not s.lstrip().startswith('#')]
assert lines(p/'expected-normalized.sdc')==lines(p/'final-normalized.sdc')
assert not any(re.match(r'set_(false_path|multicycle_path|disable_timing)\b',s) for s in lines(p/'final-normalized.sdc'))
drivers=[s.split('\t') for s in (p/'drivers.tsv').read_text().splitlines()];selected=set((R/'cu/C-outputs.txt').read_text().splitlines());assert len(drivers)==len(selected)==153 and {r[0] for r in drivers}==selected and all(r[3]=='BUF_X8' for r in drivers)
assert dict(s.split('\t') for s in (p/'pg.tsv').read_text().splitlines())=={'VDD':'1','VSS':'1'}
rcx=bound_receipt(a/'rcx/material/receipt.json');assert rcx['passed'] and not rcx['geometry_differences'] and rcx['canonical_readback_material_exact'] and rcx['components_bpins_specialnets_byte_exact']
assert sha(a/'rcx/before.def')==sha(res/'6_final.def') and sha(a/'rcx/after.def')==sha(res/'6_post_rcx.def')
manifest(a/'rcx/inputs-before.sha256');assert (a/'rcx/inputs-before.sha256').read_bytes()==(a/'rcx/inputs-after.sha256').read_bytes()
focus=obj(a/'focused/receipt.json');assert focus['diagnostics_clear']
fm=manifest(a/'focused/inputs-before.sha256');assert fm[str(res/'6_final.gds')]==sha(res/'6_final.gds');assert (a/'focused/inputs-before.sha256').read_bytes()==(a/'focused/inputs-after.sha256').read_bytes()
for name in ('upper','antenna'):
 report=a/'focused'/(name+'.lyrdb');assert sha(report)==focus[name]['report_sha256'] and not ET.parse(str(report)).findall('.//items/item')
full=obj(f/'receipt.json');assert full['full_foundry_deck_passed'] and full['full_deck_items']==0
report=f/'full.lyrdb';assert not ET.parse(str(report)).findall('.//items/item') and sha(report)==full['report_sha256']
assert full['deck_sha256']=='4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147'
fm=manifest(f/'inputs-before.sha256');assert (f/'inputs-before.sha256').read_bytes()==(f/'inputs-after.sha256').read_bytes()
assert fm['/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc']==full['deck_sha256']
for ext in ('gds','odb','sdc','spef','v'):assert fm[str(res/('6_final.'+ext))]==sha(res/('6_final.'+ext))
native=bound_receipt(a/'native/classification/receipt.json');assert native['native_markers_resolved'] and not native['unresolved_indices'];assert len(native['markers'])==native['count']
for row in native['markers']:assert row['kind']=='Metal Spacing' and row['layer'] in ('metal2','metal3') and row['disposition']=='explained_same_net_continuous_material'
assert native['inputs_sha256'][str(res/'6_final.gds')]==sha(res/'6_final.gds');manifest(a/'native/inputs-before.sha256')
pg=bound_receipt(a/'pg-boundary/receipt.json');assert pg['passed'] and pg['normalized_to_candidate_PG_specialwire_material_exact'] and pg['normalized_to_candidate_PG_BPins_exact'];assert pg['uncached_PG']==[['VDD','0','1'],['VSS','0','1']]
for row in pg['all_final_pin_checks']:assert row['same_named_sbox_covers'] and row['opposite_rail_disjoint'] and row['actual_gds_covers']
pgprior=obj(a/'pg-boundary/prior-PG-disposition-binding.json');assert sha(pgprior['source_pg_disposition'])==pgprior['source_pg_disposition_sha256'];assert pgprior['current_receipt_sha256']==sha(a/'pg-boundary/receipt.json')
root=obj(a/'root-final-disposition.json');assert root['approved'];assert root['source_gds_sha256']==sha(res/'6_final.gds') and root['full_report_sha256']==sha(report) and root['native_receipt_sha256']==sha(a/'native/classification/receipt.json') and root['pg_receipt_sha256']==sha(a/'pg-boundary/receipt.json')
g=bound_receipt(a/'G-leaf-integration-binding.json');assert g['passed'] and g['selected_driver_count']==33 and g['actual_C_config_sha256']==sha(run/'config.mk');hashes(g['accepted_leaf_evidence'])
export=bound_receipt(q/'actual-export-binding.json');assert export['export_verified'] and export['saved_final_verilog_exact'];assert sha(q/'fresh-from-odb.v')==sha(res/'6_final.v')==sha(p/'final-from-odb.v')
proof=bound_receipt(q/'proof/complete-equivalence-receipt.json');assert proof['passed'];assert sha(q/'proof/gate.v')==sha(res/'6_final.v')
for k in ('formal/receipt.json','controls-tag-v3-packed/receipt.json'):
 rr=bound_receipt(q/'proof'/k);assert rr['passed']
hashes(proof['receipts'])
for path in proof['receipts']:bound_receipt(path)
mm=manifest(m/'inputs-before.sha256');assert (m/'inputs-before.sha256').read_bytes()==(m/'inputs-after.sha256').read_bytes()
for ext in ('odb','sdc','spef','gds'):assert mm[str(res/('6_final.'+ext))]==sha(res/('6_final.'+ext))
for sub in (m,m/'parent-abstract'):
 z=bound_receipt(sub/'model-import-receipt.json');assert z['passed'] and z['directions_exact'] and z['time_unit']=='1ns'
coverage=bound_receipt(m/'parent-abstract/obstruction-coverage.json');assert coverage['passed'] and coverage['pins_die_direction_exact'] and coverage['upper_metal_obs_exact'] and coverage['lower_metal_obs_conservatively_covers_raw']
release=R/'audit/C-final-release-v1';assert not release.exists();release.mkdir()
files={}
for src,target in [(res/('6_final.'+e),'6_final.'+e) for e in ('odb','def','v','sdc','spef','gds')]+[(run/'config.mk','config.mk'),(m/'cfj_group_c_memory_legacy.lib','cfj_group_c_memory_legacy.lib'),(m/'cfj_group_c_memory_legacy.lef','cfj_group_c_memory_legacy.raw.lef'),(m/'parent-abstract/cfj_group_c_memory_legacy.lef','cfj_group_c_memory_legacy.parent.lef')]:
 dst=release/target;shutil.copyfile(str(src),str(dst));assert sha(dst)==sha(src);os.chmod(str(dst),0o444);files[str(dst)]={'sha256':sha(dst),'source':str(src)}
receipt={'passed':True,'accepted_by_checks':True,'role':'C','source_run':str(run),'scope':'Macro/block nominal standalone TT contract only. Actual A/B top RC loading, P-related paths and multi-PVT qualification are not included.','period_ns':4,'frequency_MHz':250,'uncertainty_ns':.1,'setup_slack_ns':slacks['setup'],'hold_slack_ns':slacks['hold'],'counts':counts,'selected_parent_drivers':153,'selected_G_leaf_drivers':33,'driver_master':'BUF_X8','full_deck_items':0,'native_markers':native['count'],'native_disposition':'Each same-source marker independently explained; exact root disposition and complete original GDS deck zero bound.','signal_die_macro_geometry_exact':True,'PG_boundary_original_removed':pg['original_to_candidate_BPins_removed'],'PG_boundary_original_added':pg['original_to_candidate_BPins_added'],'RCX_actual_pre_post_nets_checked':rcx['nets_checked'],'source_artifacts':{str(res/('6_final.'+e)):sha(res/('6_final.'+e)) for e in ('odb','def','gds','sdc','spef','v')},'evidence_sha256':evidence,'release_files':files}
(release/'accepted-parent.json').write_text(json.dumps(receipt,indent=2));(release/'manifest.json').write_text(json.dumps({'files':files,'accepted_receipt_sha256':sha(release/'accepted-parent.json')},indent=2));print(release)
