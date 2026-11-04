from pathlib import Path
import sys,json,hashlib,zipfile,copy,subprocess
b=Path(r'D:\Data\电路实验');r=b/'LLMHardwareDesign-worktrees/issue-162-control';out=b/'control162-cluster1670';assert not out.exists();out.mkdir();src=r/'work/YUZE-LU/162/continuation-proof-89';ix=json.loads((src/'index.json').read_bytes());sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
with zipfile.ZipFile(src/'selected-originals.zip')as z:
 n='r256-composition-453/cap-candidates/16060/physical-graph.json';data=z.read(n);row=next(v for v in ix['files'].values()if v['zip_entry']==n);assert hashlib.sha256(data).hexdigest()==row['sha256'];(out/'physical-graph.json').write_bytes(data)
base_path=b/'control162-lp1664/placement.json';manifest_path=b/'control162-congestion1597/physical.json';graph_path=b/'control162-snapshot1582/boundary-graph.json';base=json.loads(base_path.read_bytes());manifest=json.loads(manifest_path.read_bytes());graph=json.loads((out/'physical-graph.json').read_bytes());solution=json.loads((b/'control162-milp1666/receipt.json').read_bytes());assert solution['feasible']
proposal=dict(schema='control162-rigid-cluster-shifts/1',candidate_only=True,whole_system_qualified=False,base_sha256=sha(base_path),manifest_sha256=sha(manifest_path),graph_sha256=sha(graph_path),shifts_um=solution['shifts']);path=out/'proposal.json';path.write_text(json.dumps(proposal,indent=2),encoding='utf-8');sys.path.insert(0,str(r/'project/experiments/control_v1'));from cluster_shift_proposal import apply
candidate,proof,bindings=apply(path,base_path,manifest_path,graph_path,base,manifest,graph);assert proof['actual_pin_reconstruction_pending'] and not proof['whole_system_qualified']
zero=copy.deepcopy(proposal);zero['shifts_um']={n:[0,0]for n in proposal['shifts_um']};zp=out/'zero.json';zp.write_text(json.dumps(zero));unchanged,_,_=apply(zp,base_path,manifest_path,graph_path,base,manifest,graph);assert unchanged==base
mutants=[]
def bad(label,fn):
 d=copy.deepcopy(proposal);fn(d);p=out/(label+'.json');p.write_text(json.dumps(d))
 try:apply(p,base_path,manifest_path,graph_path,base,manifest,graph)
 except AssertionError:mutants.append(label)
 else:raise AssertionError('Invalid proposal accepted '+label)
bad('offgrid',lambda d:d['shifts_um'].__setitem__('controller',[1,0]));bad('overbound',lambda d:d['shifts_um'].__setitem__('controller',[516,0]));bad('missing-cluster',lambda d:d['shifts_um'].pop('controller'));bad('changed-graph',lambda d:d.__setitem__('graph_sha256','0'*64));bad('claim-qualification',lambda d:d.__setitem__('whole_system_qualified',True))
cases=[[],['--reuse-placement','none'],['--reuse-placement','none','--cap-lower-bound-only','--s-translation-proposal','none'],['--reuse-placement','none','--cap-lower-bound-only','--lock-native-output-routes']]
for i,args in enumerate(cases):
 target=out/('cli-'+str(i));p=subprocess.run([sys.executable,str(r/'project/experiments/control_v1/system_upper.py'),'--manifest','none','--graph','none','--out',str(target),'--cluster-translation-proposal','none',*args],capture_output=True,text=True,cwd=r);assert p.returncode and 'Cluster shifts require' in p.stderr and not target.exists(),p.stderr
for f in ['cluster_shift_proposal.py','system_upper.py']:compile((r/'project/experiments/control_v1'/f).read_bytes(),f,'exec')
(out/'candidate-math-only.json').write_text(json.dumps(candidate),encoding='utf-8');(out/'receipt.json').write_text(json.dumps(dict(passed=True,inputs=bindings,zero_shift_exact=True,real345_nonoverlap=True,independent_fresh_native_pin_reconstruction_executed=False,proposal_mutants_rejected=mutants,illegal_contexts_rejected=len(cases),whole_system_qualified=False,scope='Local candidate/data/context verification only; actual EDA/native-pin/cap diagnostic not yet executed. Math result is not an accepted placement.'),indent=2),encoding='utf-8');print(json.dumps(dict(passed=True,instances=len(candidate['placements_um']),mutants=len(mutants),contexts=len(cases),proposal=str(path))))
