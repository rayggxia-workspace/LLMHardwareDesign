"""Read-only scientific artifact pair receipt; no tensor/model execution."""
import argparse, hashlib, json
from pathlib import Path

def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b)
    return h.hexdigest()

def indexed(root):
    root=Path(root).resolve();mp=root/'manifest.json';m=json.loads(mp.read_text())
    raw=m['artifacts'];rows=raw if isinstance(raw,list) else [dict(path=k,**v)for k,v in raw.items()]
    if len({r['path']for r in rows})!=len(rows):raise ValueError('duplicate artifact')
    files={}
    for row in rows:
        name=row['path'];p=(root/name).resolve()
        if Path(name).is_absolute() or not p.is_relative_to(root) or p==root:raise ValueError('unsafe path')
        v=dict(bytes=p.stat().st_size,sha256=sha(p))
        if v!={k:row[k]for k in ('bytes','sha256')}:raise ValueError('actual artifact SHA/bytes mismatch '+str(p))
        files[name]=v
    return dict(path=str(root),manifest_sha256=sha(mp),manifest_status=m.get('status'),
                producer_sha256=m.get('source',{}).get('transport_sha256'),files=files)

p=argparse.ArgumentParser();p.add_argument('--pair',nargs=3,action='append',required=True,metavar=('LABEL','LEFT','RIGHT'));p.add_argument('--out',type=Path,required=True);a=p.parse_args()
if a.out.exists():raise ValueError('refuse receipt overwrite')
result=dict(schema='issue70-scientific-pair-readback-v1',scope='fresh artifact SHA/size equality only; original model/native/diagnostic statuses unchanged',pairs=[])
for label,left,right in a.pair:
    l,r=indexed(left),indexed(right)
    names=sorted(set(l['files'])|set(r['files']))
    pairs=[dict(path=n,left=l['files'].get(n),right=r['files'].get(n),identical=l['files'].get(n)==r['files'].get(n) and n in l['files'] and n in r['files'])for n in names]
    passed=bool(pairs)and all(x['identical']for x in pairs)and isinstance(l['producer_sha256'],str)and len(l['producer_sha256'])==64 and l['producer_sha256']==r['producer_sha256']
    result['pairs'].append(dict(label=label,status='PASS'if passed else'FAIL',left={k:v for k,v in l.items()if k!='files'},right={k:v for k,v in r.items()if k!='files'},artifacts=pairs))
result['status']='PASS'if all(x['status']=='PASS'for x in result['pairs'])else'FAIL'
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+'\n',encoding='utf-8')
print(json.dumps(dict(status=result['status'],pairs=[dict(label=x['label'],status=x['status'],artifacts=len(x['artifacts']))for x in result['pairs']],receipt_sha256=sha(a.out))))
raise SystemExit(0 if result['status']=='PASS'else 1)
