from pathlib import Path
import subprocess,shlex,json,hashlib,base64,time
h=Path(__file__).parent;r=h/'LLMHardwareDesign-worktrees/issue-162-control';out=r/'work/YUZE-LU/162/continuation-proof-65';assert not out.exists()
q=r'''from pathlib import Path
import json,hashlib,base64,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');files=[]
for name in ['r256-phase-trace-regression-718','r256-phase-source-and-regression-audit-725','r256-final-chain-binding-audit-726','r256-directional-bidirectional-active-pool-audit-728','r256-real-phase-timing-731']:
 assert json.loads((b/name/'receipt.json').read_text())['passed'];files+=list((b/name).rglob('*'))
files+=list((b/'r256-node7-live-readback-719').rglob('*'))
for prefix in ['sready718-','sready723-']:
 matches=[p for p in(b/'route-selection-102').iterdir()if p.name.startswith(prefix)];assert len(matches)==1;files+=list(matches[0].rglob('*'))
files += [b/'source-717/source-manifest.json',b/'source-717/freeze-import.json']
for folder,seed in [('dynamic-07/node7',7200)]:
 for section in ['commands','pending']:
  for p in(b/folder/section).glob('*.json'):
   if p.stem.endswith('-'+str(seed)):files.append(p)
 files.append(b/'r256-composition-453'/('acceptance-'+str(seed)+'.json'))
rows=[]
for p in sorted(set(files)):
 if not p.is_file():continue
 raw=p.read_bytes();copy=p.suffix in ['.json','.txt','.log','.cpp','.h','.py']and len(raw)<2000000
 row=dict(relative=str(p.relative_to(b)),path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),copied=copy)
 if copy:row['base64']=base64.b64encode(raw).decode()
 rows.append(row)
print(json.dumps(dict(time=time.time(),rows=rows,whole_system_qualified=False)))
'''
compile(q,'remote-proof704','exec');d=json.loads(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=60));out.mkdir()
for row in d['rows']:
 if row['copied']:
  raw=base64.b64decode(row.pop('base64'));assert hashlib.sha256(raw).hexdigest()==row['sha256'];p=out/row['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
items={}
for n in [717,718,719,722,723,724,725,726,727,728,729,730,731]:
 for p in h.glob('control162-*.py'):
  if p.stem.endswith(str(n))or p.stem.endswith(str(n)+'-remote'):items['helpers/'+p.name]=p
for n in [706,721]:items['helpers/publication-'+str(n)+'.json']=h/('control162-git-data-publish-'+str(n))/'receipt.json'
for directory in ['control162-phase727','control162-watch686']:
 fs=sorted((h/directory).glob('*.json'))
 for p in [fs[0],fs[-1]]:items['selected-running-snapshots/'+directory+'/'+p.name]=p
d['helpers']=[]
for name,p in items.items():
 raw=p.read_bytes();target=out/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);d['helpers'].append(dict(relative=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
d['metadata_failures']=dict(generator722='Closing-parenthesis slicing mistake rejected by compile before helper write or remote changes; corrected generator compiled before use.',audit728_initial='Actual7200 inputs not generated yet; precondition rejected before audit output creation or any mutation. Same audit later passed16 input pairs and16 real PIDs. Original failing helper source replaced only to shorten Python exception display and clarify current scope; earlier invocation did not alter remote tasks.')
d['scope']='Source717 optional bounded phase timer only; actual full718 regression retains prior tests and adds3 trace cases/output-filtered-log exact replays,27 weighted cases total/8 rejects. Fourteen invariant gate/resource/scene/prepass/pool sources and exact original finite/class bytes. Actual16 child processes/input pairs/memory and7 future final-chain specs checked. Only guarded own old4760 step reallocated; preserved source/spec/logs; eight parents retain36 slots576 CPUs and dynamic refill. Selected phase snapshots software time only, not hardware waveform or whole-system physical qualification.'
(out/'index.json').write_bytes((json.dumps(d,indent=2)+'\n').encode());print(json.dumps(dict(rows=len(d['rows']),copied=sum(x['copied']for x in d['rows']),helpers=len(d['helpers']))))
