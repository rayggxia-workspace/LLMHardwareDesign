from pathlib import Path
import subprocess,shlex,json,hashlib,base64,shutil,time
r=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control');home=r.parent.parent;out=r/'work/YUZE-LU/162/continuation-proof-43/supplement-277';assert not out.exists()
q=r'''from pathlib import Path
import json,hashlib,time,base64
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');files={}
for stem in ['source-276','r256-placement-regression-277','r256-early-electrical-266/initial','r256-early-electrical-266/optimized','r256-early-electrical-277/optimized','r256-early-native-279','route-selection-102/sready277-r256-placement-envelope','route-selection-102/sready279-early-native','dynamic-07/node7']:
 root=b/stem
 for p in root.rglob('*'):
  if p.suffix in ['.json','.log','.rpt','.txt','.tcl']and (stem!='source-276'or p.name in ['source-manifest.json','freeze-import.json']):files[p]=True
rows=[]
for p in sorted(files):
 raw=p.read_bytes();row=dict(path=str(p),relative=str(p.relative_to(b)),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),capture_time=time.time(),active_prefix_snapshot=True)
 if len(raw)<=524288:row['base64']=base64.b64encode(raw).decode()
 rows.append(row)
print(json.dumps(dict(captured_at=time.time(),rows=rows,whole_system_qualified=False,scope='Source276 exact R256 placement/search contract, actual old full byte replay, five rejected inputs, actual16 independently verified R256 placement costs and native diagnostic admission; later source-binding supplement only, no physical qualification.')))
'''
compile(q,'supplement277','exec');d=json.loads(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=55));out.mkdir();count=0
for row in d['rows']:
 encoded=row.pop('base64',None);row['copied']=encoded is not None
 if encoded is not None:
  raw=base64.b64decode(encoded);assert hashlib.sha256(raw).hexdigest()==row['sha256'];p=out/row['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);count+=1
helpers=[]
for n in ['control162-placement-queue277.py','control162-placement-status278.py','control162-pinbbox279.py','control162-r256-early-native279.py','control162-watch-r256280.py','control162-capture-supplement277.py']:
 p=out/'helpers'/n;p.parent.mkdir(exist_ok=True);shutil.copyfile(home/n,p);helpers.append(dict(relative=str(p.relative_to(out)),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size))
d.update(copied_count=count,helpers=helpers);(out/'index.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(indexed=len(d['rows']),copied=count,helpers=len(helpers),captured_at=d['captured_at'])))
