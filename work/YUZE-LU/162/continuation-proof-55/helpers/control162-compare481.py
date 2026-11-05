import subprocess,shlex
q="""from pathlib import Path
import json,time,hashlib,statistics
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453/upper-candidates';out=b/'r256-controlled-high-weight-comparison-481';assert not out.exists();sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();bindings={};metrics={};comparisons=[]
for i in range(16):
 a=root/'4661/route'/('trial-'+str(i))/'input.txt';c=root/'4760/route'/('trial-'+str(i))/'input.txt';ar=a.read_text();cr=c.read_text();ah,ab=ar.split('\\n',1);ch,cb=cr.split('\\n',1);av=ah.split();cv=ch.split();assert ab==cb and av[:5]==cv[:5]and av[6:]==cv[6:]and av[5]=='16'and cv[5]=='128';comparisons.append(dict(trial=i,baseline_input_sha256=sha(a),candidate_input_sha256=sha(c),only_initial_weight_field_differs=True))
for seed in [4661,4760]:
 rounds={};resources={};progress=[]
 for f in(root/str(seed)/'route').glob('trial-*/router.log'):
  raw=f.read_bytes();bindings[str(f)]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),active_prefix_snapshot=True)
  events=[json.loads(x)for x in raw.decode().splitlines()if x.startswith('{')]
  for x in events:
   if 'conflict_nodes'in x:rounds.setdefault(x['round'],[]).append(x)
   if 'maximum_resource_labels'in x:resources.setdefault(x['round'],[]).append(x)
  if events and 'routed'in events[-1]:progress.append(events[-1]['routed'])
 summary={}
 for n,rows in rounds.items():
  summary[str(n)]=dict(observed_trials=len(rows),mean_conflict_positions=statistics.mean(x['conflict_nodes']for x in rows),mean_excess_occupancy=statistics.mean(x['excess_occupancy']for x in rows),mean_summed_tree_vertices=statistics.mean(x['summed_tree_vertices']for x in rows),max_resource_labels=max([x['maximum_resource_labels']for x in resources.get(n,[])]or[0]))
 metrics[str(seed)]=dict(rounds=summary,current_routed_progress_range=[min(progress),max(progress)]if progress else None)
out.mkdir();d=dict(captured_at=time.time(),passed=True,compared_trials=16,input_comparisons=comparisons,log_snapshot_bindings=bindings,metrics=metrics,whole_system_qualified=False,scope='Controlled actual453 placement4610/RNG4661/cost2/scale1/critical-first/8million labels/64attempts16active. All16 raw trial input bytes differ only initial weight16 vs128. Metrics compare complete round cohorts and both conflict positions/excess occupancy; no exact round duration inferred from untimestamped logs. More completed rounds at capture does not prove convergence, wire legality or system qualification.');(out/'receipt.json').write_text(json.dumps(d,indent=2));print(json.dumps(metrics))
"""
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
