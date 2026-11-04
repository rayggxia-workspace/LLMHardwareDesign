from pathlib import Path
import subprocess,shlex,json,hashlib,base64,time
h=Path(__file__).parent;r=h/'LLMHardwareDesign-worktrees/issue-162-control';out=r/'work/YUZE-LU/162/continuation-proof-70';assert not out.exists()
q=r'''from pathlib import Path
import json,hashlib,base64,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');files=[]
for name in ['r256-native-prefix-path-diagnostic-873','r256-native-snapshot-source-audit-875','r256-native-headroom-audit-881','r256-native-zero-regression-885','r256-maze-legacy45-byte-audit-887','r256-final-chain-binding-audit-890','r256-directional-bidirectional-active-pool-audit-891','r256-native-batch-regression-902','r256-maze-legacy45-byte-audit-907','r256-final-chain-binding-audit-911','r256-directional-bidirectional-active-pool-audit-918']:
 p=b/name;assert(p/'receipt.json').exists(),name;assert json.loads((p/'receipt.json').read_text())['passed'],name
 files += [x for x in p.rglob('*')if x.is_file()and x.suffix in ['.json','.txt','.log','.cpp','.h','.py']]
for prefix in ['sready873-','sready876-','sready885-','sready889-','sready902-','sready905-','sready915-']:
 matches=[p for p in(b/'route-selection-102').iterdir()if p.name.startswith(prefix)];assert matches,prefix
 for p in matches:files += [x for x in p.rglob('*')if x.is_file()]
for name in ['r256-native-batch-admission-904','r256-native-batch-admission-914']:
 files += [x for x in(b/name).rglob('*')if x.is_file()]
for n in [872,884,901]:files += [b/('source-'+str(n))/'source-manifest.json',b/('source-'+str(n))/'freeze-import.json']
for folder,tags in [('dynamic-08/node6',[8860,9060,9061]),('dynamic-03/node5',[8861,8862,9062,9063])]:
 queue=b/folder;files.append(queue/'queue-state.json')
 for tag in tags:
  route=b/'r256-composition-453/upper-candidates'/str(tag)/'route';files+=list(route.glob('trial-*/router.log'))+list(route.glob('trial-*/output.txt.native-prefix.log'))+list(route.glob('trial-*/output.txt.pin-access.json'))+list(route.glob('trial-*/input.txt'));files += [route/'router-input.txt',b/'r256-composition-453'/('acceptance-'+str(tag)+'.json')]
  for section in ['commands','pending']:
   for p in(queue/section).glob('*.json'):
    d=json.loads(p.read_text());args=d.get('args',d.get('command',[]))
    if any('/upper-candidates/'+str(tag)+'/'in a for a in args):files.append(p)
rows=[]
for p in sorted(set(files)):
 if not p.is_file():continue
 raw=p.read_bytes();copy=p.suffix in ['.json','.txt','.log','.cpp','.h','.py']and len(raw)<4000000
 row=dict(relative=str(p.relative_to(b)),path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),copied=copy)
 if copy:row['base64']=base64.b64encode(raw).decode()
 rows.append(row)
print(json.dumps(dict(time=time.time(),rows=rows,whole_system_qualified=False)))
'''
compile(q,'proof917remote','exec');d=json.loads(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=120));out.mkdir()
for row in d['rows']:
 if row['copied']:
  raw=base64.b64decode(row.pop('base64'));assert hashlib.sha256(raw).hexdigest()==row['sha256'];p=Path(chr(92)*2+'?'+chr(92)+str(out/row['relative']));p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
items={}
for p in h.glob('control162-*.py'):
 if p.is_file()and any(p.stem.endswith(str(n))or p.stem.endswith(str(n)+'-remote')for n in range(869,920)):items['helpers/'+p.name]=p
for n in [870,877,892,903]:items['publication-'+str(n)+'.json']=h/('control162-git-data-publish-'+str(n))/'receipt.json'
for folder in ['control162-native-repair897','control162-native-repair912','control162-batch-fixture899']:
 for p in(h/folder).iterdir():
  if p.is_file():items['local-analysis/'+folder+'/'+p.name]=p
for folder in ['control162-native-progress896','control162-native-progress916','control162-read908','control162-progress913']:
 fs=sorted((h/folder).glob('*.json'))
 if fs:items['selected-snapshots/'+folder+'/'+fs[-1].name]=fs[-1]
d['helpers']=[]
for name,p in items.items():
 raw=p.read_bytes();target=Path(chr(92)*2+'?'+chr(92)+str(out/name));target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);d['helpers'].append(dict(relative=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
d['scope']='Actual87316 original failed native snapshots/log replays;88563case40negative/887every57old byte replay;90271case45negative/907every63old byte replay incl native logs.901 adds opt-in batch dirty-native ripup and ordinary-only upfront exits, original18 physical/resource/helper sources and finite/exact branches unchanged.911four28stage configs actual453functions/events and all future final gates bound.915 retires only guarded own8860/1/2 after902/907/911 pass,905 earlier exact8591 retired for regression; all raw sources/specs/partials preserved.897/912 bounded local snapshot A* analyses do NOT find complete18net repair;899 fixed fixture genuinely exercises batch across19rounds, independently checked again in902.9060-9063 live logs are byte snapshots at index time, never completed acceptance.23 native types/138 files and R256/S1350/state ownership remain unchanged.8parent c64 4x16/c96 6x16 dynamic; node6/node5 forecasts224GiB need284.8GiB actual available. Other own/foreign/externalR work preserved. No complete fullscene route, geometry/PG/3RC300MHz or joint qualification inferred.'
d['previous_evidence']=dict(commit='0b8fbf260fbdb486868b0607ec00f3c449b0d6d8',path='work/YUZE-LU/162/continuation-proof-69/index.json')
(out/'index.json').write_bytes((json.dumps(d,indent=2)+'\n').encode());print(json.dumps(dict(rows=len(d['rows']),copied=sum(x['copied']for x in d['rows']),helpers=len(d['helpers']))))
