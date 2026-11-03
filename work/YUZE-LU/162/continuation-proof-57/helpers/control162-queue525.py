from pathlib import Path
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453';source=b/'source-524';record=b/'route-selection-102/sready525-progressive-search-window';assert not record.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();rows=[]
def put(name,spec):
 p=b/'dynamic-02/node3/pending'/(name+'.json');assert not p.exists();tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
reg=b/'r256-ordinary-window-regression-525'
put('00-f-sready525-progressive-window-regression',dict(script='system_upper.py',source_root=str(source),forecast_gib=16,requires=[],args=['--manifest',str(b/'r256-composition-359/selected/physical.json'),'--graph',str(root/'topology/boundary-graph.json'),'--directional-regression-only','--route-regression-baseline',str(b/'source-510/project/experiments/control_v1/tree_router.cpp'),'--out',str(reg)]))
template=[x for x in json.loads((b/'route-selection-102/sready519-ordinary-cost-grid/tasks.json').read_text())['tasks']if '-5191'in Path(x['path']).stem];assert len(template)==7
config=root/'acceptance-5260.json';assert not config.exists();config.write_text((root/'acceptance-5191.json').read_text().replace('/upper-candidates/5191/','/upper-candidates/5260/'))
for old in template:
 spec=json.loads(json.dumps(old['spec']));spec['source_root']=str(source)
 for key in ['args','requires']:spec[key]=[x.replace('/upper-candidates/5191/','/upper-candidates/5260/').replace('acceptance-5191.json','acceptance-5260.json')for x in spec[key]]
 if spec['script']=='system_upper.py':
  a=spec['args'];assert a[a.index('--seed')+1]=='4661'and a[a.index('--route-ordinary-congestion-scale')+1]=='64';a+=['--route-ordinary-search-margin','64'];spec['requires']+=[str(reg/'receipt.json')]
 put(Path(old['path']).stem.replace('sready519','sready526').replace('5191','5260'),spec)
gates={}
for name in ['system_geometry.py','system_sta.py','system_accept.py','final_composition.py','native_pin_load.py','native_cap_residual.py','upper_cap_bound.py','steiner_wire_bound.py','placement_residual_budget.py','resource_search.h']:
 p=source/'project/experiments/control_v1'/name;assert sha(p)==sha(b/'source-510/project/experiments/control_v1'/name);gates[name]=sha(p)
old=(b/'source-510/project/experiments/control_v1/tree_router.cpp').read_text();new=(source/'project/experiments/control_v1/tree_router.cpp').read_text();start='    if(pareto_wire_budget&&n<locked_count&&wire_limits[n]>=0){';end='    }else if(bidirectional_two_terminal';assert old.split(start,1)[1].split(end,1)[0]==new.split(start,1)[1].split(end,1)[0]
record.mkdir();(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,unchanged_final_and_resource_sha256=gates,finite_resource_branch_byte_identical=True,whole_system_qualified=False,scope='Actual ordinary search remains slow after concrete494 heap diagnosis; test early software locality window without changing hardware, finite weak-output search or any physical budget/gate. First actual525 full existing regression plus4new real window cases/5rejects/default510bytes. Controlled5260 same actual453 placement4611/RNG4661/cost2/h256/adaptive/ordinary64 as5191; only ordinary search window64 added, containing existing tree/target, widened every4rounds and full grid fromround64. Window failure explicitly does not prove global infeasibility. Full original7 final geometry/PG/threeRC300MHz/current453function/joint gates retained; no convergence/speed/route qualification claim. Own node3 replacement only after exact UID/step/graph/source/4failed-old-fixed-trials guard; original outputs/source/spec retained, no foreign/R/parent cancellation.'),indent=2));print(json.dumps(dict(queued=len(rows),candidate=5260)))
'''
compile(q,'queue525','exec');Path(__file__).with_name('control162-queue525-remote.py').write_bytes(q.encode());print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
