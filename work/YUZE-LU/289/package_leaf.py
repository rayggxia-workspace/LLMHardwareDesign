"""Freeze an accepted leaf and its parent-ready abstract; never overwrite releases."""
import hashlib,json,shutil,sys
from pathlib import Path
role,source,target=sys.argv[1:]
c=Path(source).resolve(); out=Path(target).resolve()
assert role in ('G','S')
proof=json.loads((c/'accepted-leaf.json').read_text())
assert proof['passed'] and proof['role']==role
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
for path,digest in proof['sha256'].items():assert sha(path)==digest,path
abstract=c/'parent-abstract-v3'
ap=json.loads((abstract/'receipt.json').read_text());assert ap['passed']
for path,digest in ap['sha256'].items():assert sha(path)==digest,path
name='block_v2_g' if role=='G' else 'local_s_base'
nickname='bv1_block_v2_g' if role=='G' else 'local_s_base'
sources={f'{name}.{ext}':c/f'candidate.{ext}' for ext in ('odb','def','v','sdc','spef')}
sources.update({f'{name}.lef':abstract/f'{name}.lef',f'{name}.lib':c/'qualification-v2'/f'{name}.lib',f'{name}.gds':c/'qualification-v2/flow/results/nangate45'/nickname/'base/6_final.gds','accepted-leaf.json':c/'accepted-leaf.json','abstract-receipt.json':abstract/'receipt.json'})
out.mkdir(parents=True,exist_ok=False)
manifest={}
for name,p in sources.items():
    shutil.copyfile(p,out/name)
    digest=sha(p);assert sha(out/name)==digest
    manifest[name]={'source':str(p),'sha256':digest}
(out/'manifest.json').write_text(json.dumps({'role':role,'scope':'Accepted leaf only; parent and top timing require their own receipts','files':manifest},indent=2)+'\n')
print(json.dumps({'role':role,'output':str(out),'files':len(manifest),'verified':True}))
