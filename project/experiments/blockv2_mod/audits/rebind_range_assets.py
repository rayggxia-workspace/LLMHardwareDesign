"""Reuse identical sealed inputs only after graph/base/allocation equality."""
from pathlib import Path
import json,sys,os
from native_package_runtime import load
from macro_assets import filehash
old,new,assets,out=map(Path,sys.argv[1:])
om,op,_=load(old);nm,np,_=load(new)
if om['graph_sha256']!=nm['graph_sha256'] or op['storage.json']!=np['storage.json'] or op['hardware.json']!=np['hardware.json']:
 raise ValueError('input reuse requires identical graph/base/storage')
a=json.loads(assets.read_text())
if a['plan_sha256']!=om['plan_sha256']:raise ValueError('old input plan mismatch')
out.mkdir(parents=True,exist_ok=False)
for row in a['regions']:
 source=(assets.parent/row['file']).resolve();target=out/row['file']
 if not source.is_relative_to(assets.parent.resolve()) or filehash(source)!=row['sha256']:raise ValueError('asset seal')
 target.parent.mkdir(parents=True,exist_ok=True);os.link(source,target)
a.update(plan_sha256=nm['plan_sha256'],rebound_from_plan_sha256=om['plan_sha256'],
 input_reuse_proof='identical graph, hardware and full storage plus every asset SHA256')
(out/'assets.json').write_text(json.dumps(a,indent=2)+'\n')
