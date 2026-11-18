"""Source-side closure enumeration; the script returns metadata, not weights."""
REMOTE = r'''
import hashlib,json,os,sys
from pathlib import Path
model=sys.argv[1]
base=Path('/public/home/yuzelu/Melodydt/runs/issue-274')
root=base/('three-p-gemma-q12-02' if model=='gemma' else 'three-p-full-01')
variant='kv64' if model in ('llama','granite') else 'cache'
files={p for p in root.iterdir() if p.is_file() and p.suffix in ('.py','.cpp','.sha256','.sbatch','.txt')}
expected={}
stages={}
for mode in ('prefill','decode'):
    run='run-116000' if model=='gemma' else 'run-{}-{}'.format(115618 if mode=='prefill' else 115619,model)
    stage=root/run/('{}-w4-{}-pr272-combined'.format('prefill' if mode=='prefill' else 'decode-live',variant))
    stages[mode]=str(stage)
    files.update(p for p in stage.rglob('*') if p.is_file())
    plan=(stage/'assets/plan.json').read_bytes()
    result=json.loads((stage/'result.json').read_text())
    if hashlib.sha256(plan).hexdigest()!=result['plan_sha256']:
        raise ValueError('frozen plan mismatch')
    for entry in json.loads(plan)['images']:
        path=Path(entry['path'])
        path.relative_to(base)
        files.add(path)
        expected[str(path)]=entry['sha256']
rows=[]
for p in sorted(files):
    p.relative_to(base)
    if p.is_symlink(): raise ValueError('symbolic input')
    digest=expected.get(str(p))
    if digest is None:
        h=hashlib.sha256()
        with p.open('rb') as f:
            for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
        digest=h.hexdigest()
    rows.append(dict(source=str(p),bytes=p.stat().st_size,sha256=digest))
print(json.dumps(dict(model=model,baseline=stages,source_root=str(root),baseline_commit='fbff1bd0e455739f28d9b7dd00b97216fe7bb847',files=rows)))
'''
