from pathlib import Path
import subprocess,shlex,json,hashlib,base64,time
h=Path(__file__).parent;r=h/'LLMHardwareDesign-worktrees/issue-162-control';out=r/'work/YUZE-LU/162/continuation-proof-68';assert not out.exists()
q=r'''from pathlib import Path
import json,hashlib,base64,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');files=[]
for name in ['r256-threshold-pattern-regression-791','r256-endpoint-escape-regression-810','r256-final-chain-binding-audit-802','r256-threshold-source-invariant-audit-803','r256-threshold-full-regression-audit-804','r256-directional-bidirectional-active-pool-audit-807','r256-older-placement-live-readback-793','r256-older-placement-live-readback-815','r256-final-chain-binding-audit-816','r256-escape-legacy39-byte-audit-817','r256-directional-bidirectional-active-pool-audit-818','r256-actual-pin-endpoint-probe-822']:
 assert json.loads((b/name/'receipt.json').read_text())['passed'];files+=list((b/name).rglob('*'))
for prefix in ['sready791-','sready799-','sready805-','sready810-','sready813-','sready814-']:
 matches=[p for p in(b/'route-selection-102').iterdir()if p.name.startswith(prefix)];assert len(matches)==1;files+=list(matches[0].rglob('*'))
for n in [790,809]:files += [b/('source-'+str(n))/'source-manifest.json',b/('source-'+str(n))/'freeze-import.json']
for folder,tag in [('dynamic-06/node26',7920),('dynamic-06/node26',7921),('dynamic-05/node2',8110),('dynamic-05/node4',8111)]:
 p=b/'r256-composition-453/upper-candidates'/str(tag)/'route';files+=list(p.glob('trial-*/router.log'));files += [p/'router-input.txt',p/'trial-0/input.txt',b/'r256-composition-453'/('acceptance-'+str(tag)+'.json')]
 for section in ['commands','pending']:
  files += [p for p in(b/folder/section).glob('*.json')if p.stem.endswith('-'+str(tag))]
rows=[]
for p in sorted(set(files)):
 if not p.is_file():continue
 raw=p.read_bytes();copy=p.suffix in ['.json','.txt','.log','.cpp','.h','.py']and len(raw)<4000000
 row=dict(relative=str(p.relative_to(b)),path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),copied=copy)
 if copy:row['base64']=base64.b64encode(raw).decode()
 rows.append(row)
print(json.dumps(dict(time=time.time(),rows=rows,whole_system_qualified=False)))
'''
compile(q,'proof823-remote','exec');d=json.loads(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=60));out.mkdir()
for row in d['rows']:
 if row['copied']:
  raw=base64.b64decode(row.pop('base64'));assert hashlib.sha256(raw).hexdigest()==row['sha256'];p=out/row['relative'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
items={}
for n in [790,791,795,798,799,800,802,803,804,805,807,808,809,810,813,814,815,816,817,818,821,822,823]:
 for p in h.glob('control162-*'):
  if p.is_file()and p.suffix in ['.py','.cpp']and(p.stem.endswith(str(n))or p.stem.endswith(str(n)+'-remote')or p.name=='control162-source'+str(n)+'-prepare.py' or p.name=='control162-endpoint-probe'+str(n)+'-driver.py'):items['helpers/'+p.name]=p
for name in ['control162-static795.py','control162-static-verify798.py']:items['helpers/'+name]=h/name
for p in(h/'control162-static795').iterdir():
 if p.is_file():items['static-pin-diagnostics/'+p.name]=p
for n in [794,796,819]:items['publication-'+str(n)+'.json']=h/('control162-git-data-publish-'+str(n))/'receipt.json'
fs=sorted((h/'control162-watch797').glob('*.json'));items['running-snapshot/'+fs[-1].name]=fs[-1]
d['helpers']=[]
for name,p in items.items():
 raw=p.read_bytes();target=out/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);d['helpers'].append(dict(relative=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
d['scope']='Actual791 full39case threshold regression, actual810 full45case escape regression, actual817 every39 disabled-default input/output/filtered-log byte replay against actual791,33 std-heap/3trace/3W1 and original oracles retained. Fifteen final/resource/scene/prepass/pool/weighted sources and original exact/finite branches unchanged. Actual822 real9730pair static capped-candidate probe with independent5000273 unit-step checks covers all static pairs after2317 extra escape hits; ignores simultaneous congestion/history and is not a route qualification. Only guarded own5491/5492 and7371/7370 child steps replaced; old raw/spec/source/failure/partial outputs preserved. Actual32 plus32 new router children/input bytes/16CPU/memory and two14spec complete final-chain bindings checked. Existing accepted23native types/138files and345 state owners/current453 functions/traces remain referenced through current363/472/473/480/536, not requalified by these software tests. No grid/native/physical gate relaxation or speed/convergence/system pass claim. All final geometry/PG/low-base-high300MHz/joint gates remain mandatory.806 descriptive pair-window label superseded by807; raw prior806 remains on server.818 first precondition probe preceded all inputs; no output replaced; actual audit rerun only when ready.'
(out/'index.json').write_bytes((json.dumps(d,indent=2)+'\n').encode());print(json.dumps(dict(rows=len(d['rows']),copied=sum(x['copied']for x in d['rows']),helpers=len(d['helpers']))))
