"""Fail-closed U release aggregation. Run inside pinned ORFS container after all jobs finish."""
from pathlib import Path
import sys,json,re,hashlib,shutil,os,xml.etree.ElementTree as ET
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117')
run=Path(sys.argv[1]).resolve();assert str(run).startswith(str(root)+'/')
audit=root/'audit';name=run.name;proof=audit/(name+'-independent-v3');full=audit/('full-'+name);model=audit/('model-'+name);focused=audit/('focused-'+name)
res=next((run/'flow/results/nangate45').glob('*/*'))
physical_run=Path(os.environ.get('U_PHYSICAL_EVIDENCE_RUN',str(run))).resolve()
full=audit/('full-'+physical_run.name);focused=audit/('focused-'+physical_run.name)
cache={}
def sha(p):
 p=Path(p).resolve()
 if p not in cache:
  h=hashlib.sha256()
  with p.open('rb') as f:
   for buf in iter(lambda:f.read(1024*1024),b''):h.update(buf)
  cache[p]=h.hexdigest()
 return cache[p]
def obj(p):return json.loads(Path(p).read_text())
def manifest(path):
 rows={}
 for line in path.read_text().splitlines():
  h,p=line.split(maxsplit=1);p=p.lstrip('*');assert re.fullmatch('[0-9a-f]{64}',h);assert sha(p)==h,('Changed input',p);rows[str(Path(p).resolve())]=h
 return rows
bound=obj(proof/'inputs-before.json');assert bound==obj(proof/'inputs-after.json')
for source,h in bound.items():assert sha(source)==h,('Independent evidence input changed',source)
assert bound[str(res/'6_final.odb')]==sha(res/'6_final.odb')
counts={a:int(b) for a,b in (s.split() for s in (proof/'counts.tsv').read_text().splitlines())}
assert set(counts)=={'setup','hold','capacitance','slew','fanout'} and not any(counts.values()),counts
slacks={k:float(re.search(r'worst slack (?:max|min)\s+([-+0-9.eE]+)',(proof/(k+'.rpt')).read_text())[1]) for k in ('setup','hold')};assert min(slacks.values())>=0,slacks
for p in ('async.rpt','electrical.rpt'):assert 'VIOLATED' not in (proof/p).read_text().upper(),p
selected=set((root/'cu/U-outputs.txt').read_text().splitlines());drivers=[s.split('\t') for s in (proof/'drivers.tsv').read_text().splitlines()]
assert len(drivers)==153 and {s[0] for s in drivers}==selected and len(selected)==153
for row in drivers:
 assert row[3]=='BUF_X8',row
pg=dict(s.split('\t') for s in (proof/'pg.tsv').read_text().splitlines());assert pg=={'VDD':'1','VSS':'1'},pg
contract=obj(proof/'sdc-contract.json');assert contract['passed'] and contract['selected_load_fF']==50 and contract['period_ns']==4
for p,h in contract['hashes'].items():assert sha(p)==h,p
# Independently compare original reference to final signal/die/macro geometry.
def geometry(p):
 rows=set(p.read_text().splitlines());power={s for s in rows if s.startswith(('PIN\tVDD\t','PIN\tVSS\t'))};return rows-power,power
orig,opg=geometry(proof/'original-geometry.tsv');final,fpg=geometry(proof/'final-geometry.tsv');assert orig==final
_,knownpg=geometry(audit/'U-v13-electrical-f50-x4-independent-v2/final-geometry.tsv');assert fpg==knownpg,'Undeclared PG BPin change'
for p in (proof/'formal/receipt.json',proof/'controls-v4/receipt.json'):
 r=obj(p);assert r['passed'],p
 for source,h in r.get('hashes',r.get('input_hashes',{})).items():assert sha(source)==h,source
assert obj(proof/'controls-v4/receipt.json')['state_count']==12080
control=obj(proof/'controls-v4/receipt.json')
assert control['input_hashes'][str(proof/'formal/gate-physical.json')]==sha(proof/'formal/gate-physical.json')
assert 'read_verilog '+str(res/'6_final.v') in (proof/'formal/gate-parse.ys').read_text()
manifest(proof/'proof-scripts.sha256')
assert obj(proof/'formal/receipt.json')['hashes'][str(res/'6_final.v')]==sha(res/'6_final.v')
assert Path((full/'source-run.txt').read_text().strip()).resolve()==physical_run
extraction=None
if physical_run!=run:
 physical_res=next((physical_run/'flow/results/nangate45').glob('*/*'))
 for ext in ('odb','def','v','gds','sdc'):assert sha(res/('6_final.'+ext))==sha(physical_res/('6_final.'+ext)),('Physical evidence identity mismatch',ext)
 extraction=obj(run/'extraction-binding.json');assert extraction['passed']
 for p,h in extraction['source_sha256'].items():assert sha(p)==h,p
 assert extraction['qualified_spef_sha256']==sha(res/'6_final.spef')
 for p in extraction['physical_equivalence_reports']:
  assert obj(p)['passed'],p
 assert extraction['uncached_post_rcx_pg']=={'VDD':1,'VSS':1}
assert (full/'inputs-before.sha256').read_bytes()==(full/'inputs-after.sha256').read_bytes();fm=manifest(full/'inputs-before.sha256')
physical_res=next((physical_run/'flow/results/nangate45').glob('*/*'))
for ext in ('gds','odb','v','sdc'):assert fm[str(physical_res/('6_final.'+ext))]==sha(res/('6_final.'+ext)),('Full evidence not candidate-bound',ext)
deck='/OpenROAD-flow-scripts/flow/platforms/nangate45/drc/FreePDK45.lydrc'
assert fm[deck]=='4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147'
fr=obj(full/'receipt.json');assert fr['full_foundry_deck_passed'] and fr['full_deck_items']==0
assert fr['deck_sha256']=='4e35cad6786f21c6e233fb606bea59bb44e1a12713008cf7367d65a1a3de2147'
assert len(ET.parse(str(full/'full.lyrdb')).findall('.//items/item'))==0
assert sha(full/'full.lyrdb')==fr['report_sha256']
focus=obj(focused/'receipt.json');assert focus['diagnostics_clear'] and focus['upper']['count']==0 and focus['antenna']['count']==0
assert Path((focused/'source-run.txt').read_text().strip()).resolve()==physical_run
assert (focused/'inputs-before.sha256').read_bytes()==(focused/'inputs-after.sha256').read_bytes();focus_inputs=manifest(focused/'inputs-before.sha256');assert focus_inputs[str(physical_res/'6_final.gds')]==sha(res/'6_final.gds')
assert (model/'inputs-before.sha256').read_bytes()==(model/'inputs-after.sha256').read_bytes();model_inputs=manifest(model/'inputs-before.sha256');manifest(model/'models.sha256');manifest(model/'standard-library.sha256')
for ext in ('odb','sdc','spef'):assert model_inputs[str(res/('6_final.'+ext))]==sha(res/('6_final.'+ext)),('Model not candidate-bound',ext)
for path in re.findall(r'^export ADDITIONAL_LIBS\s*=\s*(.*)$',(run/'config.mk').read_text(),re.M)[-1].split():assert model_inputs[str(Path(path).resolve())]==sha(path)
mr=obj(model/'model-import-receipt.json');assert mr['passed'] and mr['directions_exact'] and mr['time_unit'].lower()=='1ns'
for source,h in mr['source_sha256'].items():assert sha(source)==h,source
lib=model/'u_n32_controlled_dma_64.lib';lef=model/'u_n32_controlled_dma_64.lef';assert lib.stat().st_size>1000 and lef.stat().st_size>1000
assert re.search(r'cell\s*\(\s*"?u_n32_controlled_dma_64"?\s*\)',lib.read_text())
# Model LEF must preserve the externally visible signal interface exactly.
sys.path.insert(0,str(audit));from compare_lef import parse
view=parse(lef);expected={};directions={}
for line in final:
 s=line.split('\t')
 if s[0]=='PIN':expected.setdefault(s[1],[]).append([s[3],*map(int,s[4:])]);directions[s[1]]=s[2]
for port,boxes in expected.items():
 assert view['pins'].get(port)==sorted(boxes),('Model signal pin geometry mismatch',port)
 assert view['terms'][port][0]==directions[port],port
parent_model=model/'parent-abstract'
assert (parent_model/'inputs-before.sha256').read_bytes()==(parent_model/'inputs-after.sha256').read_bytes()
parent_inputs=manifest(parent_model/'inputs-before.sha256')
assert parent_inputs[str(res/'6_final.gds')]==sha(res/'6_final.gds')
assert parent_inputs[str(lef)]==sha(lef) and parent_inputs[str(lib)]==sha(lib)
for filename in ('model-import-receipt.json','obstruction-coverage.json'):
 pr=obj(parent_model/filename);assert pr['passed']
 for source,h in pr['source_sha256'].items():assert sha(source)==h,source
assert sha(parent_model/'u_n32_controlled_dma_64.lib')==sha(lib)
artifacts={p.name:dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size) for p in [res/('6_final.'+x) for x in ('odb','def','v','gds','sdc','spef')]+[lib,lef]}
p=parent_model/'u_n32_controlled_dma_64.lef';artifacts['parent_routing_lef']=dict(path=str(p),sha256=sha(p),bytes=p.stat().st_size)
evidence=[parent_model/'model-import-receipt.json',parent_model/'obstruction-coverage.json',parent_model/'inputs-before.sha256',proof/'counts.tsv',proof/'setup.rpt',proof/'hold.rpt',proof/'async.rpt',proof/'drivers.tsv',proof/'pg.tsv',proof/'sdc-contract.json',proof/'formal/receipt.json',proof/'controls-v4/receipt.json',full/'receipt.json',full/'inputs-before.sha256',focused/'receipt.json',model/'inputs-before.sha256',model/'models.sha256',model/'model-import-receipt.json',proof/'inputs-before.json',proof/'inputs-after.json']
if extraction:evidence.append(run/'extraction-binding.json')
receipt=dict(extraction_qualification=extraction,physical_evidence_source=str(physical_run),passed=True,accepted_by_checks=True,role='U',source_run=str(run),period_ns=4,frequency_MHz=250,corner='Nangate45 typical and exact bound macro models; nominal standalone contract',setup_slack_ns=slacks['setup'],hold_slack_ns=slacks['hold'],counts=counts,selected_x8_drivers=153,async_no_violations=True,power_connected=pg,full_foundry_deck_items=0,signal_die_macro_geometry_exact=True,power_bpin_removed=sorted(opg-fpg),power_bpin_added=sorted(fpg-opg),formal_state_controls_passed=True,artifacts=artifacts,evidence_sha256={str(p):sha(p) for p in evidence},scope='Macro/block qualification under the documented 50 fF selected-output IO contract. No actual A/B top interconnect RC or multi-corner/PVT robustness claim.',parent_routing_abstract_cut_contract=obj(parent_model/'obstruction-coverage.json'),project_review_status='pending parent PR workflow')
out=audit/('release-'+name);out.mkdir()
(out/'accepted-parent.json').write_text(json.dumps(receipt,indent=2))
(out/'manifest.json').write_text(json.dumps(dict(artifacts=artifacts,evidence=receipt['evidence_sha256'],accepted_parent_sha256=sha(out/'accepted-parent.json')),indent=2));print(json.dumps(dict(accepted_parent=str(out/'accepted-parent.json'),sha256=sha(out/'accepted-parent.json'),setup_ns=slacks['setup'],hold_ns=slacks['hold']),indent=2))
