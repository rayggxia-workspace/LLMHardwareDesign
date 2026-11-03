from pathlib import Path
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453';source=b/'source-537';record=b/'route-selection-102/sready540-s-translated-full-upper';assert not record.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();rows=[];np=root/'cap-necessary-538/5380/native-pin-load';assert json.loads((np/'receipt.json').read_text())['passed'];r=json.loads((np/'native-pin-load.json').read_text());assert len(r['placements'])==1 and all(x==0 for x in r['placements'][0]['violations'].values());assert r['placements'][0]['placement']==str(root/'cap-candidates/5380')
replay=[]
for scale in [16,64,256]:
 for name in ['router-input.txt','router-output.txt','router.log']:
  old=b/'r256-ordinary-cost-regression-511'/('ordinary-scale-'+str(scale))/name;new=b/'r256-ordinary-window-regression-525'/('ordinary-scale-'+str(scale))/name;assert old.read_bytes()==new.read_bytes();replay.append(dict(scale=scale,name=name,old_sha256=sha(old),new_sha256=sha(new),equal=True))
for folder in ['r256-padding-program-events-473','r256-padding-program-event-audit-480']:assert json.loads((b/folder/'receipt.json').read_text())['passed']
template=[x for x in json.loads((b/'route-selection-102/sready511-separate-ordinary-cost/tasks.json').read_text())['tasks']if '-5120'in Path(x['path']).stem];assert len(template)==7
config=root/'acceptance-5400.json';assert not config.exists();config.write_text((root/'acceptance-5120.json').read_text().replace('/upper-candidates/5120/','/upper-candidates/5400/'))
for old in template:
 spec=json.loads(json.dumps(old['spec']));spec['source_root']=str(source)
 for key in ['args','requires']:spec[key]=[x.replace('/upper-candidates/5120/','/upper-candidates/5400/').replace('acceptance-5120.json','acceptance-5400.json').replace('/cap-candidates/4610','/cap-candidates/5380').replace('/cap-necessary-461/4610/','/cap-necessary-538/5380/')for x in spec[key]]
 if spec['script']=='system_upper.py':
  a=spec['args'];assert a[a.index('--seed')+1]=='4661'and a[a.index('--route-ordinary-congestion-scale')+1]=='64'and '--route-ordinary-search-margin'not in a;spec['requires']+=[str(b/'r256-ordinary-window-regression-525/receipt.json'),str(b/'r256-padding-program-events-473/receipt.json'),str(b/'r256-padding-program-event-audit-480/receipt.json')]
 p=b/'dynamic-04/node25/pending'/(Path(old['path']).stem.replace('sready512','sready540').replace('5120','5400')+'.json');assert not p.exists();tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
gates={}
for name in ['system_geometry.py','system_sta.py','system_accept.py','final_composition.py','native_pin_load.py','native_cap_residual.py','upper_cap_bound.py','steiner_wire_bound.py','placement_residual_budget.py','resource_search.h','tree_router.cpp','tree_router_cpp.py']:
 p=source/'project/experiments/control_v1'/name;assert sha(p)==sha(b/'source-524/project/experiments/control_v1'/name);gates[name]=sha(p)
record.mkdir();(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,unchanged_router_and_final_source_sha256=gates,actual_all3_ordinary_default_replays=replay,whole_system_qualified=False,scope='Actual5380 source537 reconstructed every real pin/PG and independently checked S-only translation, all other positions/masks/die unchanged,271pairHPWL1,133,196um and1229constrained endpoint nets exact. Actual native-ground/minimum-pin/strong-tree necessary low/base/high0 completed. Full5400 same original4610 scene/RNG4661/cost2/h256/adaptive/ordinary64/no window as5120; physical S origin changes7572,4076->5504,1984 only. Actual511vs525 three ordinary-scale input/output/log bytes all identical, core537 matches actual525 source. No speed/convergence/route qualification claim. Same actual453 graph and all23fixed views/345statehosts, zero-delay programs and actual473/480 event audit completed; no physical timing inheritance. Original complete7stage geometry/nativeXOR/PG/low-base-highRC300MHz/currentfunction/joint gates unchanged, final trace supplement separately bound by index. Own node25 naturally fills completed538diagnostic slot; no extra parent, task cancellation or hardware change.'),indent=2));print(json.dumps(dict(queued=len(rows),candidate=5400,necessary_violations=r['placements'][0]['violations'])))
'''
compile(q,'queue540','exec');Path(__file__).with_name('control162-queue540-remote.py').write_bytes(q.encode());print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
