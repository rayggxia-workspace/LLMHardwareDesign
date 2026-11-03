import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');record=b/'route-selection-102/sready373-reset53-upper';p=record/'tasks.json';d=json.loads(p.read_text());rows=[]
for r in d['tasks']:
 s=r['spec'];a=s['args']
 if '--reuse-placement'in a:
  seed=int(a[a.index('--seed')+1]);place=Path(a[a.index('--reuse-placement')+1]);assert place.name==('3691'if seed in [3733,3741,3751]else'3690');assert s['source_root']==str(b/'source-358');rows.append(dict(seed=seed,actual_placement=str(place),actual_spec=r['path'],spec_sha256=r['sha256'],router=a[a.index('--router')+1]if '--router'in a else'cpp'))
assert len(rows)==8
out=record/'actual-per-candidate-placement.json';assert not out.exists();out.write_text(json.dumps(dict(time=time.time(),tasks_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),actual_route_candidates=rows,scope='Authoritative actual per-spec reuse placement: five3690 and three3691. Original tasks.json selected_placement summary variable contains only last loop3691; it is not the placement of all candidates. All eight immutable actual commands verified, no command or physical qualification changed.',whole_system_qualified=False),indent=2));print('actual_per_spec_placements',[(r['seed'],Path(r['actual_placement']).name,r['router'])for r in rows])
for folder in ['dynamic-05/node2','dynamic-02/node3','dynamic-05/node4','dynamic-04/node25','dynamic-07/node7','dynamic-02/node6']:
 d=json.loads((b/folder/'queue-state.json').read_text());print(folder,[n for n in d['active']if'sready373'in n])
'''
print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=40).decode())
