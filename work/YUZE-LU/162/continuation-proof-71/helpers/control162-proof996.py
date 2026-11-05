from pathlib import Path
import subprocess,shlex,json,hashlib,base64,time
h=Path(__file__).parent;r=h/'LLMHardwareDesign-worktrees/issue-162-control';out=r/'work/YUZE-LU/162/continuation-proof-71';assert not out.exists()
q='''from pathlib import Path
import json,hashlib,base64,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');files={}
names=['r256-native-refresh-regression-927','r256-native-refresh-source-audit-934','r256-final-chain-binding-audit-936','r256-pin-release-regression-948','r256-pin-release-source-audit-950','r256-final-chain-binding-audit-956','r256-pin-release-active-pool-audit-961','r256-native-warm-regression-973','r256-native-warm-source-audit-980','r256-final-chain-binding-audit-984','r256-native-warm-active-pool-audit-989','r256-final-chain-binding-audit-994']
for name in names:
 p=b/name;assert json.loads((p/'receipt.json').read_text())['passed'],name
 for f in p.rglob('*'):
  if not f.is_file()or f.suffix not in ['.json','.txt','.log','.py','.h']:continue
  relative=str(f.relative_to(p))
  copy=f.name=='receipt.json'or('/unchanged-'not in str(f)and any(x in relative for x in ['/refresh-8/','/refresh-16/','/full-977/','/full-979/','/same-prefix-','/refresh8-release-','/invalid-','/seed-','/manifest-','/native-pass-global-fail/']))
  files[f]=copy
for prefix in ['sready937-','sready948-','sready955-','sready957-','sready973-','sready976-','sready981-','sready983-','sready992-','sready995-']:
 matches=[p for p in(b/'route-selection-102').iterdir()if p.name.startswith(prefix)]
 for p in matches:
  for f in p.rglob('*'):
   if f.is_file():files[f]=True
for name in ['r256-native-batch-admission-931','r256-native-batch-admission-953','r256-warm-variant-admission-991','r256-final-chain-binding-audit-982']:
 for f in(b/name).rglob('*'):
  if f.is_file():files[f]=True
for n in [926,947,972]:
 for leaf in ['source-manifest.json','freeze-import.json']:files[b/('source-'+str(n))/leaf]=True
for n in [948,973]:files[b/('config'+str(n)+'.json')]=True
for n in [934,950,980]:files[b/('backout'+str(n)+'.json')]=True
for seed in [9810,9811,9920,9921]:
 root=b/'r256-composition-453';files[root/('warm-seed-'+str(seed)+'.json')]=True;files[root/('acceptance-'+str(seed)+'.json')]=True
rows=[]
for p,copy in sorted(files.items()):
 if not p.is_file():continue
 raw=p.read_bytes();copy=copy and len(raw)<6000000
 row=dict(relative=str(p.relative_to(b)),path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),copied=copy)
 if copy:row['base64']=base64.b64encode(raw).decode()
 rows.append(row)
print(json.dumps(dict(time=time.time(),rows=rows,whole_system_qualified=False,route_qualified=False)))
'''
d=json.loads(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=110));out.mkdir()
for row in d['rows']:
 if row['copied']:
  raw=base64.b64decode(row.pop('base64'));assert hashlib.sha256(raw).hexdigest()==row['sha256'];p=Path(chr(92)*2+'?'+chr(92)+str(out/row['relative']));p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
items={}
for p in h.glob('control162-*.py'):
 if any(p.stem.endswith(str(n))or p.stem.endswith(str(n)+'-remote')for n in range(924,996)):items['helpers/'+p.name]=p
for n in [922,963,964,975]:items['publication-'+str(n)+'.json']=h/('control162-git-data-publish-'+str(n))/'receipt.json'
for folder in ['control162-frozen-disconnection940','control162-warm-probe969']:
 for p in(h/folder).glob('*'):
  if p.is_file()and p.suffix in ['.json','.txt','.log']:items['local-diagnostics/'+folder+'/'+p.name]=p
for folder in ['control162-native-progress959','control162-native-progress985','control162-progress990','control162-read979','control162-read986','control162-watch987']:
 fs=sorted((h/folder).glob('*.json'))
 if fs:items['live-snapshots/'+folder+'/'+fs[-1].name]=fs[-1]
d['helpers']=[]
for name,p in items.items():
 raw=p.read_bytes();target=Path(chr(92)*2+'?'+chr(92)+str(out/name));target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);d['helpers'].append(dict(relative=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
d.update(previous_evidence=dict(commit='20ea91a8d2dac332196661dcffa63e0b30453642',path='work/YUZE-LU/162/continuation-proof-70/index.json'),scope='Selective raw capture: all indexed files independently hashed; only copied:true files embedded. Repeated unchanged71-case assets remain remotely indexed to avoid duplicating previous evidence. Actual927/934,948/950/961,973/980/989 plus strict seven-stage bindings936/956/984/994.940/941/944/966 local static diagnostic proves frozen upper prefix causes114 hard-disconnections after proxy release, not physical acceptance.972 adds validated movable M11/M12 seed reuse with original finite budgets; actual9732full-route positives/16rejects and old71/release/refresh actual byte replays. All final geometry/PG/3RC300MHz gates and M1-M10 interiors unchanged. Four current453 fullchains9810/1,9920/1 continue; no complete fullscene zero-conflict routing or system qualification yet. Failed982 stale audit assertions retained, fixed984 passed. Exact own9490/9491/8110/8111 guards preserve raw/source/spec/partials,8parents and36x16 dynamic slots, externalR/foreign untouched. Live snapshots are time-bounded metadata only.')
(out/'index.json').write_text(json.dumps(d,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(rows=len(d['rows']),copied=sum(x['copied']for x in d['rows']),helpers=len(d['helpers']))))
