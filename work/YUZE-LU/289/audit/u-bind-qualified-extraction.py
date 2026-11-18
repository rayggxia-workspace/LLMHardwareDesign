from pathlib import Path
import hashlib,json,re
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');dst=r/'audit/U-antenna/candidate-U-v16-qualified';orig=r/'audit/U-v15-pg-diagnostic';ext=r/'u-physical/rcx-def-uncached-119788/normal'
reports=[r/'audit/U-normalized-gds-records.json',r/'u-physical/rcx-material-119791/material.json']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
res=dst/'flow/results/nangate45/u-overlay-current/base';source=orig/'flow/results/nangate45/u-overlay-current/base'
for x in ('odb','def','v','gds','sdc'):assert sha(res/('6_final.'+x))==sha(source/('6_final.'+x))
assert sha(res/'6_final.spef')==sha(ext/'isolated.spef')
log=(ext/'run.log').read_text()
for rail in ('VDD','VSS'):assert f'AFTER_RCX_PG {rail} CATCH=0 RESULT=1' in log
assert 'BEFORE_RCX_PG' not in log,'Precheck could cache PG result'
paths=[ext/'run.log',ext/'isolated.spef',ext/'before.def',ext/'after.def',r/'u-physical/rcx-normalized-119778/normalized.def']+reports
for p in reports:
 v=json.loads(p.read_text());assert v['passed'];
 for sourcepath,h in v['source_sha256'].items():assert sha(Path(sourcepath))==h
paths += list(res.glob('6_final.*'))
v=dict(passed=True,physical_source=str(orig),qualified_spef_sha256=sha(res/'6_final.spef'),uncached_post_rcx_pg={'VDD':1,'VSS':1},physical_equivalence_reports=list(map(str,reports)),source_sha256={str(p):sha(p) for p in paths},scope='Same-width NDR metadata normalization in extraction copy; both normalized input and extracted output GDS material must exactly equal original. Original physical delivery ODB/DEF/V/GDS/SDC retained; qualified SPEF replaced and standalone timing/model re-evaluated.')
p=dst/'extraction-binding.json';assert not p.exists();p.write_text(json.dumps(v,indent=2));print(p)
