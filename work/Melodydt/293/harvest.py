"""Package only completed, accepted probe receipts; preserve failed job evidence."""
from pathlib import Path
from hashlib import sha256
import json,zipfile,subprocess
r=Path(__file__).resolve().parent
manifest={}
with zipfile.ZipFile(r/'accepted-results.zip','w',zipfile.ZIP_DEFLATED) as z:
    for run in sorted(r.glob('run-*')):
        for p in run.glob('*/samples.json'):
            data=json.loads(p.read_bytes())
            assert data['passed'] and all(x['equal'] for x in data['numerical'])
            name=str(p.relative_to(r))
            z.write(p,name);manifest[name]=sha256(p.read_bytes()).hexdigest()
        for name in ('source-commit.txt','scripts.sha256','results.sha256','cpu.txt','python-version.txt','memory.txt'):
            p=run/name
            if p.exists():z.write(p,str(p.relative_to(r)))
    z.writestr('accepted-manifest.json',json.dumps(manifest,indent=2))
print('ACCEPTED',len(manifest))
