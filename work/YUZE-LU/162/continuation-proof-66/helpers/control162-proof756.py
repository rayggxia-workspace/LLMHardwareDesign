from pathlib import Path
import subprocess,shlex,json,hashlib,base64,time
h=Path(__file__).parent;r=h/'LLMHardwareDesign-worktrees/issue-162-control';out=r/'work/YUZE-LU/162/continuation-proof-66';assert not out.exists()
q=r'''from pathlib import Path
import json,hashlib,base64,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');files=[]
for name in ['r256-pair-window-regression-736','r256-pair-window-source-and-regression-audit-745','r256-final-chain-binding-audit-746','r256-directional-bidirectional-active-pool-audit-751','r256-older-placement-live-readback-739','r256-pair-window-phase-comparison-757','r256-older-placement-live-readback-760','r256-final-chain-binding-audit-764','r256-directional-bidirectional-active-pool-audit-765']:
 assert json.loads((b/name/'receipt.json').read_text())['passed'];files+=list((b/name).rglob('*'))
for tag in [7370,7371,7580,7581]:files+=list((b/'r256-composition-453/upper-candidates'/str(tag)/'route').glob('trial-*/router.log'))
for prefix in ['sready736-','sready741-','sready742-','sready761-','sready762-','sready763-']:
 matches=[p for p in(b/'route-selection-102').iterdir()if p.name.startswith(prefix)];assert len(matches)==1;files+=list(matches[0].rglob('*'))
files += [b/'source-735/source-manifest.json',b/'source-735/freeze-import.json']
for folder,seed in [('dynamic-05/node4',7370),('dynamic-05/node2',7371),('dynamic-02/node3',7580),('dynamic-04/node25',7581)]:
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
for n in [734,735,736,739,740,741,742,744,745,746,748,749,750,751,752,755,756,757,760,761,762,763,764,765]:
 for p in h.glob('control162-*.py'):
  if p.stem.endswith(str(n))or p.stem.endswith(str(n)+'-remote'):items['helpers/'+p.name]=p
for n in [733,743]:items['helpers/publication-'+str(n)+'.json']=h/('control162-git-data-publish-'+str(n))/'receipt.json'
for directory in ['control162-phase727','control162-phase749/7370','control162-phase749/7371','control162-phase749/7580','control162-phase749/7581','control162-watch734']:
 fs=sorted((h/directory).glob('*.json'))
 for p in [fs[0],fs[-1]]:items['selected-running-snapshots/'+directory+'/'+p.name]=p
for name in ['issue-verified','pr-request','pr-verified']:items['online747/'+name+'.json']=h/('control162-online747-'+name+'.json')
items['helpers/control162-source735-prepare.py']=h/'control162-source735-prepare.py'
d['helpers']=[]
for name,p in items.items():
 raw=p.read_bytes();target=out/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);d['helpers'].append(dict(relative=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
d['metadata_failures']=dict(source735_prepare='Local generator wrote wrapper then rejected exact system CLI substring because existing help differed. Actual system edits applied separately and archive735 hashes all four final sources; no frozen or running source modified.',phase749_initial='Initial local snapshots lacked embedded candidate ID when called with argument. They remain locally preserved but are excluded from this proof. Corrected helper embeds candidate/route-root and saves separate candidate directories; only corrected snapshots included.',compare757_compile='Missing whitespace after else rejected locally by py_compile before any remote action; corrected helper compiled and actual757 comparison raw snapshots preserved.')
d['scope']='Source735 optional pair-only window prompted by actual7200 ordinary-pair phase timing. Actual full736 retains old tests and contains33 weighted/trace/window cases,6 window cases,3 trace byte replays/3 weight1 replays/12 rejects. Fifteen invariant final/resource/scene/prepass/pool/weighted header sources and exact original finite/class bytes. Actual64 child processes/input pairs/memory and28 future full-chain specs checked. Only guarded own old4850/5190/5191/5192 steps reallocated, all raw/source/spec retained; eight parents36x16CPU unchanged. Actual757 matching completed round8 calls show no early benefit for64 on different c64 hosts;4/16 extend comparison with same already-regressed code. Running logs are partial software snapshots, not whole-round timing, complete route, hardware waveforms or physical qualification.'
(out/'index.json').write_bytes((json.dumps(d,indent=2)+'\n').encode());print(json.dumps(dict(rows=len(d['rows']),copied=sum(x['copied']for x in d['rows']),helpers=len(d['helpers']))))
