from pathlib import Path
import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453';record=b/'route-selection-102/sready500-bidirectional-signal-search';assert not record.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();assert json.loads((b/'r256-search-phase-analysis-498/receipt.json').read_text())['passed'];rows=[]
def put(name,spec):
 p=b/'dynamic-02/node6/pending'/(name+'.json');assert not p.exists();tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(p);rows.append(dict(path=str(p),sha256=sha(p),spec=spec))
reg=b/'r256-bidirectional-search-regression-500'
put('00-f-sready500-bidirectional-search-regression',dict(script='system_upper.py',source_root=str(b/'source-474'),forecast_gib=16,requires=[],args=['--manifest',str(b/'r256-composition-359/selected/physical.json'),'--graph',str(root/'topology/boundary-graph.json'),'--route-regression-only','--route-regression-baseline',str(b/'source-435/project/experiments/control_v1/tree_router.cpp'),'--out',str(reg)]))
template=[x for x in json.loads((b/'route-selection-102/sready476-controlled-high-weight/tasks.json').read_text())['tasks']if '-4760'in Path(x['path']).stem];assert len(template)==7
config=root/'acceptance-5010.json';assert not config.exists();config.write_text((root/'acceptance-4760.json').read_text().replace('/upper-candidates/4760/','/upper-candidates/5010/'))
for old in template:
 spec=json.loads(json.dumps(old['spec']))
 for key in ['args','requires']:spec[key]=[x.replace('/upper-candidates/4760/','/upper-candidates/5010/').replace('acceptance-4760.json','acceptance-5010.json')for x in spec[key]]
 if spec['script']=='system_upper.py':
  a=spec['args'];assert a[a.index('--seed')+1]=='4661'and a[a.index('--route-nonpreferred-cost')+1]=='2';a[a.index('--route-heuristic-weight')+1]='256';a.remove('--route-adaptive-heuristic');a+=['--bidirectional-two-terminal'];spec['requires']+=[str(reg/'receipt.json')]
 put(Path(old['path']).stem.replace('sready476','sready501').replace('4760','5010'),spec)
record.mkdir();(record/'tasks.json').write_text(json.dumps(dict(time=time.time(),tasks=rows,whole_system_qualified=False,scope='Actual494 exact-prefix bounded diagnosis and498 pin-role analysis identify 12 stopped single-sink S-bus searches plus4 PG searches at2million ordinary heap pops. Use existing supported balanced-potential bidirectional search for ordinary two-terminal signals; original finite-resource search retains every actual weak-output wire budget, PG/clock multi-terminal search remains original. No new router algorithm or hardware code. Precede full5010 by original full actual route regression including9bidirectional cases,100Dijkstra oracle, finite-budget rejects and default-byte replay. Same actual453 placement4610/RNG4661/cost2/scale1/critical-first/8million labels/64attempts16active. Initial256 matches4850 but adaptive must be disabled for existing supported bidi mode, so this is not a single-variable controlled comparison. All original7stage physical/PG/threeRC300MHz/actual453function/joint gates unchanged; no route/convergence/speed/system qualification claim. Own node6 dynamically fills the completed diagnostic slot, no extra parent or cancellation.'),indent=2));print(json.dumps(dict(queued=len(rows),candidate=5010)))
'''
compile(q,'queue500','exec');Path(__file__).with_name('control162-queue500-remote.py').write_bytes(q.encode());print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
