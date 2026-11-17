from pathlib import Path
import hashlib,json,re
p=Path(__file__).parent
c=p/'runs/C-v16-genericadder-cached/config.mk';u=p/'runs/U-v13-electrical-f50-x4/config.mk'
def files(f):return re.findall(r'^export ADDITIONAL_GDS = (.*)$',f.read_text(),re.M)[-1].split()
rows=[]
for token in ('issue-200-compact-local-s/run08-base0','issue-201-compact-ge/2ba89c0bd/release/e_compact'):
 a=[Path(x) for x in files(c) if token in x];b=[Path(x) for x in files(u) if token in x]
 assert len(a)==len(b)==1
 sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
 rows.append({'token':token,'C_source':str(a[0]),'U_source':str(b[0]),'C_sha256':sha(a[0]),'U_sha256':sha(b[0])})
 assert rows[-1]['C_sha256']==rows[-1]['U_sha256']
root=p.parent/'u-physical';meta=json.loads((root/'leaf-cut-obs.json').read_text())
tsv=(root/'leaf-cut-obs.tsv').read_bytes()
assert hashlib.sha256(tsv).hexdigest()==meta['tsv_sha256']
(p/'c-leaf-cut-obs.tsv').write_bytes(tsv)
(p/'c-leaf-cut-source-binding.json').write_text(json.dumps({'same_exact_leaf_source_gds':rows,'cut_extraction_metadata':meta,'scope':'Reuses exact actual leaf cuts because C and U load identical source GDS bytes; no pin/GDS changes'},indent=2)+'\n')
