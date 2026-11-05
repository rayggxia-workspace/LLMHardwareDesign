from pathlib import Path
import subprocess,shlex,json,hashlib,base64,time
h=Path(__file__).parent;r=h/'LLMHardwareDesign-worktrees/issue-162-control';out=r/'work/YUZE-LU/162/continuation-proof-64';assert not out.exists()
q=r'''from pathlib import Path
import json,hashlib,base64,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');files=[]
for name in ['r256-weighted-bidir-regression-691','r256-weighted-source-and-regression-audit-699','r256-final-chain-binding-audit-701','r256-directional-bidirectional-active-pool-audit-703','r256-old4340-4390-live-spec-readback-696']:
 assert json.loads((b/name/'receipt.json').read_text())['passed'];files+=list((b/name).rglob('*'))
for prefix in ['sready691-','sready695-','sready697-']:
 matches=[p for p in(b/'route-selection-102').iterdir()if p.name.startswith(prefix)];assert len(matches)==1;files+=list(matches[0].rglob('*'))
files += [b/'source-690/source-manifest.json',b/'source-690/freeze-import.json']
for folder,seed in [('dynamic-03/node5',6920),('dynamic-02/node3',6921)]:
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
for n in [683,684,686,687,688,690,691,694,695,696,697,698,699,701,703,704]:
 for p in h.glob('control162-*.py'):
  if p.stem.endswith(str(n))or p.stem.endswith(str(n)+'-remote'):items['helpers/'+p.name]=p
for n in [685,693]:items['helpers/publication-'+str(n)+'.json']=h/('control162-git-data-publish-'+str(n))/'receipt.json'
for p in(h/'control162-order-window687').iterdir():
 if p.is_file():items['local-static-order-window687/'+p.name]=p
for directory in ['control162-watch662','control162-watch686']:
 fs=sorted((h/directory).glob('*.json'))
 for p in [fs[0],fs[-1]]:items['selected-running-snapshots/'+directory+'/'+p.name]=p
d['helpers']=[]
for name,p in items.items():
 raw=p.read_bytes();target=out/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);d['helpers'].append(dict(relative=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
d['metadata_failures']=dict(order687='Static comparison assertion correct, but source digest field hashed reused header variable; original bytes retained and688 correction sidecar supplies correct source-block digest. Window comparisons unchanged.',read694='Output tag incorrectly used as RNG filter; no match caused assertion before any cancellation. Partial empty metadata directory retained,696 selects actual output folder and records full raw specs.',audit703_initial='Precondition before output creation found6921 real inputs not yet generated. Same audit703 later passed all32 actual input pairs and32 actual PIDs after generation.',shell_generator='PowerShell rejected one inline source patch generator during parsing before execution; actual changes applied with structured patches. No remote source or running task affected.')
d['scope']='Actual source690 full original plus24 weighted cases/1200 independent path checks/3 exact weight1 replays/4 new rejects;14 invariant gate/resource/scene/prepass/pool sources and exact original finite/class bytes;32 actual current weighted process/input/memory checks and14 full final-chain bindings. Exact own old359 reallocations and all source/spec/old partial logs retained. Initial-order windows only bound next100 candidates, not exact active net/time; snapshots selected only. No complete route or system qualification inherited.'
(out/'index.json').write_bytes((json.dumps(d,indent=2)+'\n').encode());print(json.dumps(dict(rows=len(d['rows']),copied=sum(x['copied']for x in d['rows']),helpers=len(d['helpers']))))
