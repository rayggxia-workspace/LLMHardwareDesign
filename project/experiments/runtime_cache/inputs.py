import argparse,json,hashlib
from pathlib import Path
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=argparse.ArgumentParser();p.add_argument('--old',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();m=json.loads((a.old/'manifest.json').read_text())
for e in m['artifacts']:
 if sha(a.old/e['path'])!=e['sha256']:raise ValueError('old physical SHA')
cases=json.loads((a.old/'cases.json').read_text());a.out.mkdir(exist_ok=False)
(a.out/'vectors85.tsv').write_text(''.join(c['name']+' '+str(a.old/c['payload0'])+' '+str(a.old/c['payload1'])+' '+c['gamma']+' '+str(c['coefficient'])+'\n'for c in cases))
(a.out/'cases.json').write_text(json.dumps(cases,indent=2)+'\n')
(a.out/'manifest.json').write_text(json.dumps({'schema':'runtime85-input-v1','old_root':str(a.old),'old_manifest_sha256':sha(a.old/'manifest.json'),'artifacts':[{'path':f.name,'sha256':sha(f)}for f in a.out.iterdir()if f.is_file()]},indent=2)+'\n')
print('PASS_REUSE84_INPUTS')
