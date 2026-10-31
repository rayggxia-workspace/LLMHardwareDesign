from pathlib import Path
import json,hashlib,base64,subprocess,shlex,tarfile
q=r'''from pathlib import Path
import json,hashlib,base64,datetime
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121');files={};sources={}
for n in ('826','827','828','829'):
 r=b/('block-v1-20261101-'+n)
 for p in [r/k for k in ('manifest.json','node-queue.json','dispatch-state.json','stage-identity-proof.json')]:
  raw=p.read_bytes();files[str(p.relative_to(b))]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),base64=base64.b64encode(raw).decode())
 m=json.loads((r/'src/bundle-manifest.json').read_text());sources[n]={v['path']:hashlib.sha256((r/'src'/v['path']).read_bytes()).hexdigest()for v in m['files']}
for p in (b/'admission-20261101-830').iterdir():
 if p.is_file()and p.suffix in ('.json','.pid'):
  raw=p.read_bytes();files[str(p.relative_to(b))]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),base64=base64.b64encode(raw).decode())
print(json.dumps(dict(captured_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),files=files,actual_source_sha256=sources)))'''
d=json.loads(subprocess.check_output(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]));out=Path('work/YUZE-LU/121/review-20261028/admission-830/capture-start');assert not out.exists()
for n in ('826','827','828','829'):
 with tarfile.open('.local/issue121/source'+('826'if n=='826'else'827')+'.tar')as t:
  m=json.load(t.extractfile('bundle-manifest.json'));assert d['actual_source_sha256'][n]=={v['path']:v['sha256']for v in m['files']}
  for row in m['files']:assert t.extractfile(row['path']).read()==subprocess.check_output(['git','cat-file','blob',row['git_blob']])
 prefix='block-v1-20261101-'+n+'/'
 for name,remote in [('stage'+n+'-manifest.json','manifest.json'),('node-queue-'+n+'.json','node-queue.json')]:assert hashlib.sha256((out.parent.parent/name).read_bytes()).hexdigest()==d['files'][prefix+remote]['sha256']
out.mkdir()
for name,row in d['files'].items():
 raw=base64.b64decode(row.pop('base64'));assert hashlib.sha256(raw).hexdigest()==row['sha256'];p=out/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
d.update(actual_sources_and_git_archives_verified=True,scope='Four immutable R queues/controller source and identity proof.826 source598d/364files;827-829 source747d/365files. Staging/deployment evidence only, not P&R or final acceptance.')
(out/'index.json').write_bytes((json.dumps(d,indent=2)+'\n').encode());print('831',d['captured_utc'],len(d['files']),'raw; four archives/source Git verified')
