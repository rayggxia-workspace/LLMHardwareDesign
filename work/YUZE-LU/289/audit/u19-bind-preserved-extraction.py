from pathlib import Path
import hashlib,json
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');dst=r/'audit/U-antenna/candidate-U-v19-preserved';orig=r/'audit/U-v15-pg-diagnostic';ext=r/'u-physical/rcx-def-uncached-119842/normal'
reports=[r/'audit/U-normalized-gds-records.json',r/'audit/U-canonical-transitive-v3/receipt.json',r/'audit/U-canonical-merged-v2/receipt.json']
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
res=dst/'flow/results/nangate45/u-overlay-current/base';source=orig/'flow/results/nangate45/u-overlay-current/base'
for x in ('odb','def','v','gds','sdc'):assert sha(res/('6_final.'+x))==sha(source/('6_final.'+x))
assert sha(res/'6_final.spef')==sha(ext/'isolated.spef')
log=(ext/'run.log').read_text()
for rail in ('VDD','VSS'):assert f'AFTER_RCX_PG {rail} CATCH=0 RESULT=1' in log
assert 'BEFORE_RCX_PG' not in log
trans=r/'audit/U-canonical-transitive-inputs'
assert sha(trans/'before.def')==sha(r/'u-physical/rcx-def-uncached-119788/normal/before.def')
assert sha(trans/'after.def')==sha(ext/'before.def')
paths=[ext/'run.log',ext/'isolated.spef',ext/'before.def',ext/'after.def',ext/'source.sha256',ext.parent/'u-rcx-normalized.tcl']+reports
for p in reports:
 v=json.loads(p.read_text());assert v['passed']
 if 'nets_checked' in v:assert v['nets_checked']==117231 and not v['geometry_differences'] and v['canonical_readback_material_exact'] and v['components_bpins_specialnets_byte_exact']
 for q,h in v['source_sha256'].items():assert sha(Path(q))==h;paths.append(Path(q))
paths += list(res.glob('6_final.*'))
v=dict(passed=True,physical_source=str(orig),qualified_spef_sha256=sha(res/'6_final.spef'),uncached_post_rcx_pg={'VDD':1,'VSS':1},physical_equivalence_reports=list(map(str,reports)),source_sha256={str(p):sha(p) for p in paths},scope='NDR metadata normalized with native widths; collinear net38 source segments merged with exact material union. Original physicalGDS is byte-exact to normalization input excluding only GDS timestamps. Both original-to-merged-input and merged-input-to-extracted-output have all117231net per-layer polygon union exact, plus component/BPin/specialnet byte exact. Original ODB/DEF/V/GDS/SDC preserved; only qualified SPEF replaced, followed by fresh STA/model/formal. Raw concatenated DEF streamout known to produce incorrect joined-path geometry; final delivery uses original verified GDS.')
p=dst/'extraction-binding.json';assert not p.exists();p.write_text(json.dumps(v,indent=2));print(p)
