from pathlib import Path
h=Path(r'D:\Data\电路实验');s=(h/'control162-proof823.py').read_text(encoding='utf-8').replace('continuation-proof-68','continuation-proof-69')
a=s.index("for name in ['r256-threshold-pattern");z=s.index('rows=[]',a)
s=s[:a]+'''for name in ['r256-zero-maze-regression-829','r256-final-chain-binding-audit-834','r256-maze-legacy45-byte-audit-835','r256-directional-bidirectional-active-pool-audit-837','r256-density-live-readback-839','r256-pin-exit-diagnostic-841','r256-pin-exit-diagnostic-848','r256-native-prefix-regression-855','r256-maze-legacy45-byte-audit-858','r256-pin-exit-paired-audit-860','r256-older-placement-live-readback-861','r256-final-chain-binding-audit-864','r256-directional-bidirectional-active-pool-audit-866']:
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
''' +s[z:]
a=s.index('print(json.dumps(dict(time=time.time(),rows=rows');s=s[:a]+'''for tag in [841,848]:
 report=b/('r256-pin-exit-diagnostic-'+str(tag))/'complete-paths/complete-path-diagnostics.json'
 for case in json.loads(report.read_text())['cases']:
  p=Path(case['snapshot_path']);assert p.stat().st_size==case['snapshot_bytes']
  rows.append(dict(relative=str(p.relative_to(b)),path=str(p),bytes=case['snapshot_bytes'],sha256=case['snapshot_sha256'],copied=False,sha256_origin='Actual compute diagnostic verified complete paths and recorded this SHA; current stat length verified here, large file not rehashed on login',hash_receipt=str(report),case=case['case']))
''' +s[a:]
a=s.index('for n in [790,791,795');z=s.index("d['helpers']=[]",a)
s=s[:a]+'''for n in [827,828,829,831,832,833,834,835,836,837,838,839,840,841,842,843,846,848,849,850,851,852,854,855,856,857,858,859,860,861,862,863,864,865,866,867,868]:
 for p in h.glob('control162-*'):
  if p.is_file()and p.suffix in ['.py','.cpp','.h']and(p.stem.endswith(str(n))or p.stem.endswith(str(n)+'-remote')or p.stem.endswith(str(n)+'-driver')):items['helpers/'+p.name]=p
for name in ['control162-recover859-remote.py','control162-config864-remote.py','control162-queue856-remote.py','control162-queue855.py','control162-refill863-remote.py']:items['helpers/'+name]=h/name
for p in(h/'control162-pin-matching840').iterdir():
 if p.is_file():items['static-pin-matching/'+p.name]=p
for n in [825,836,857]:items['publication-'+str(n)+'.json']=h/('control162-git-data-publish-'+str(n))/'receipt.json'
for folder in ['control162-watch862','control162-native-progress867','control162-read865']:
 fs=sorted((h/folder).glob('*.json'));items[folder+'/'+fs[-1].name]=fs[-1]
''' +s[z:]
a=s.index("d['scope']=");z=s.index("\n(out/'index.json')",a);s=s[:a]+"d['scope']='Actual829 full51case regression and835 every45 old byte replay; actual855 full57case/35negative including native-prefix-pass/global-fail and858 every51 old byte replay.17 final/resource/scene/prepass/pool/weighted sources and original exact/finite branches unchanged. Actual841/848 matched16 complete original round0 paths each with edges/vias/flood/wire checks and exact original counters, plus860 paired pin-exit observations. Static840 unique all24760 pin matching is only a static search plan. New8560/8561 native-first/all or after-native pin reservation retain all physical budgets and final7stage paths,86414spec bindings and86632actual child/input/16CPU/memory checks. Native prefix zero can never substitute for full global route or physical acceptance. Own controller95101 failed because855spec queued before854source freeze complete; all raw failures preserved, robust source269 queue97097 restores eighth parent; three interrupted7stage chains restart fresh8590/8591/8592, no old source/spec/output changed. Exact guarded own5451 child95155.117 replaced only after855/858 actual passes.8parents c64 4x16/c96 6x16 dynamic, actual1.2+16GiB memory gate retained, no foreign/externalR work touched. Large complete-path partial files remain remote, SHA recorded during actual compute diagnostics and current stat byte lengths rechecked; no expensive login rehash or false current-byte readback claim. Accepted23native types/138files/R256/S1350 internal drive and345stateownership/current453 functions/events remain preserved. No full zero-conflict route or final geometry/PG/3RC300MHz/system qualification claim.'"+s[z:]
s=s.replace("timeout=60","timeout=120");compile(s,'proof868','exec');(h/'control162-proof868.py').write_bytes(s.encode())
