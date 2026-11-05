from pathlib import Path
import subprocess,shlex,json,hashlib,base64,time
h=Path(__file__).parent;r=h/'LLMHardwareDesign-worktrees/issue-162-control';out=r/'work/YUZE-LU/162/continuation-proof-69';assert not out.exists()
q=r'''from pathlib import Path
import json,hashlib,base64,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');files=[]
for name in ['r256-zero-maze-regression-829','r256-final-chain-binding-audit-834','r256-maze-legacy45-byte-audit-835','r256-directional-bidirectional-active-pool-audit-837','r256-density-live-readback-839','r256-pin-exit-diagnostic-841','r256-pin-exit-diagnostic-848','r256-native-prefix-regression-855','r256-maze-legacy45-byte-audit-858','r256-pin-exit-paired-audit-860','r256-older-placement-live-readback-861','r256-final-chain-binding-audit-864','r256-directional-bidirectional-active-pool-audit-866']:
 assert json.loads((b/name/'receipt.json').read_text())['passed'];files+=[p for p in(b/name).rglob('*')if p.is_file()and not p.name.endswith('.partial.txt')]
for prefix in ['sready829-','sready831-','sready832-','sready841-','sready842-','sready848-','sready855-','sready859-','sready863-']:
 matches=[p for p in(b/'route-selection-102').iterdir()if p.name.startswith(prefix)and not p.name.endswith('incomplete-01')];assert matches,prefix
 for p in matches:files+=list(p.rglob('*'))
for n in [828,854]:files += [b/('source-'+str(n))/'source-manifest.json',b/('source-'+str(n))/'freeze-import.json']
for folder,tag in [('dynamic-08/node6',8560),('dynamic-03/node5',8561),('dynamic-08/node6',8590),('dynamic-08/node6',8591),('dynamic-08/node6',8592)]:
 p=b/'r256-composition-453/upper-candidates'/str(tag)/'route';files+=list(p.glob('trial-*/router.log'))+list(p.glob('trial-*/output.txt.native-prefix.log'))+list(p.glob('trial-*/output.txt.pin-access.json'));files += [p/'router-input.txt',p/'trial-0/input.txt',b/'r256-composition-453'/('acceptance-'+str(tag)+'.json')]
 for section in ['commands','pending']:
  for p in(b/folder/section).glob('*.json'):
   d=json.loads(p.read_text());args=d.get('args',d.get('command',[]))
   if any('/upper-candidates/'+str(tag)+'/'in a for a in args):files.append(p)
for folder in ['dynamic-02/node6','dynamic-08/node6']:
 p=b/folder;files+=[p/'slurm.log',p/'queue-state.json']
 files+=[x for x in(p/'previous-controller-failure').glob('*')if x.is_file()]
 files+=list(p.glob('*855*.log'))+list((p/'commands').glob('*855*.json'))+list((p/'pending').glob('*855*.json'))
rows=[]
for p in sorted(set(files)):
 if not p.is_file():continue
 raw=p.read_bytes();copy=p.suffix in ['.json','.txt','.log','.cpp','.h','.py']and len(raw)<4000000
 row=dict(relative=str(p.relative_to(b)),path=str(p),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),copied=copy)
 if copy:row['base64']=base64.b64encode(raw).decode()
 rows.append(row)
for tag in [841,848]:
 report=b/('r256-pin-exit-diagnostic-'+str(tag))/'complete-paths/complete-path-diagnostics.json'
 for case in json.loads(report.read_text())['cases']:
  p=Path(case['snapshot_path']);assert p.stat().st_size==case['snapshot_bytes']
  rows.append(dict(relative=str(p.relative_to(b)),path=str(p),bytes=case['snapshot_bytes'],sha256=case['snapshot_sha256'],copied=False,sha256_origin='Actual compute diagnostic verified complete paths and recorded this SHA; current stat length verified here, large file not rehashed on login',hash_receipt=str(report),case=case['case']))
print(json.dumps(dict(time=time.time(),rows=rows,whole_system_qualified=False)))
'''
compile(q,'proof823-remote','exec');d=json.loads(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=120));out.mkdir()
for row in d['rows']:
 if row['copied']:
  raw=base64.b64decode(row.pop('base64'));assert hashlib.sha256(raw).hexdigest()==row['sha256'];p=Path('\\\\?\\'+str(out/row['relative']));p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
items={}
for n in [827,828,829,831,832,833,834,835,836,837,838,839,840,841,842,843,846,848,849,850,851,852,854,855,856,857,858,859,860,861,862,863,864,865,866,867,868]:
 for p in h.glob('control162-*'):
  if p.is_file()and p.suffix in ['.py','.cpp','.h']and(p.stem.endswith(str(n))or p.stem.endswith(str(n)+'-remote')or p.stem.endswith(str(n)+'-driver')):items['helpers/'+p.name]=p
for name in ['control162-recover859-remote.py','control162-config864-remote.py','control162-queue856-remote.py','control162-queue855.py','control162-refill863-remote.py']:items['helpers/'+name]=h/name
for p in(h/'control162-pin-matching840').iterdir():
 if p.is_file():items['static-pin-matching/'+p.name]=p
for n in [825,836,857]:items['publication-'+str(n)+'.json']=h/('control162-git-data-publish-'+str(n))/'receipt.json'
for folder in ['control162-watch862','control162-native-progress867','control162-read865']:
 fs=sorted((h/folder).glob('*.json'));items[folder+'/'+fs[-1].name]=fs[-1]
d['helpers']=[]
for name,p in items.items():
 raw=p.read_bytes();target=Path('\\\\?\\'+str(out/name));target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(raw);d['helpers'].append(dict(relative=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest()))
d['scope']='Actual829 full51case regression and835 every45 old byte replay; actual855 full57case/35negative including native-prefix-pass/global-fail and858 every51 old byte replay.17 final/resource/scene/prepass/pool/weighted sources and original exact/finite branches unchanged. Actual841/848 matched16 complete original round0 paths each with edges/vias/flood/wire checks and exact original counters, plus860 paired pin-exit observations. Static840 unique all24760 pin matching is only a static search plan. New8560/8561 native-first/all or after-native pin reservation retain all physical budgets and final7stage paths,86414spec bindings and86632actual child/input/16CPU/memory checks. Native prefix zero can never substitute for full global route or physical acceptance. Own controller95101 failed because855spec queued before854source freeze complete; all raw failures preserved, robust source269 queue97097 restores eighth parent; three interrupted7stage chains restart fresh8590/8591/8592, no old source/spec/output changed. Exact guarded own5451 child95155.117 replaced only after855/858 actual passes.8parents c64 4x16/c96 6x16 dynamic, actual1.2+16GiB memory gate retained, no foreign/externalR work touched. Large complete-path partial files remain remote, SHA recorded during actual compute diagnostics and current stat byte lengths rechecked; no expensive login rehash or false current-byte readback claim. Accepted23native types/138files/R256/S1350 internal drive and345stateownership/current453 functions/events remain preserved. No full zero-conflict route or final geometry/PG/3RC300MHz/system qualification claim.'
(out/'index.json').write_bytes((json.dumps(d,indent=2)+'\n').encode());print(json.dumps(dict(rows=len(d['rows']),copied=sum(x['copied']for x in d['rows']),helpers=len(d['helpers']))))
