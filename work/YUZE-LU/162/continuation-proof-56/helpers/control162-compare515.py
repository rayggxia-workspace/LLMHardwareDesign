import subprocess,shlex
q=r'''from pathlib import Path
import json,hashlib,time,subprocess,statistics
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');root=b/'r256-composition-453/upper-candidates';out=b/'r256-ordinary-cost-controlled-comparison-515';assert not out.exists();sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();rows=[]
for i in range(16):
 a=root/'4850/route'/('trial-'+str(i))/'input.txt';c=root/'5120/route'/('trial-'+str(i))/'input.txt';assert a.read_bytes()==c.read_bytes();rows.append(dict(trial=i,baseline=str(a),candidate=str(c),identical_input_sha256=sha(a)))
binary=root/'5120/route/router';code="import os,json;rows=[]\nfor n in os.listdir('/proc'):\n if not n.isdigit():continue\n try:\n  p='/proc/'+n;assert os.stat(p).st_uid==10011\n  if os.readlink(p+'/exe')=="+repr(str(binary))+":\n   cmd=open(p+'/cmdline','rb').read().decode().split(chr(0));rows.append(dict(pid=n,command=[x for x in cmd if x]))\n except (OSError,AssertionError):pass\nprint(json.dumps(rows))"
procs=json.loads(subprocess.check_output(['srun','--jobid=95101','--overlap','-n1','-c1','python3','-c',code],universal_newlines=True));assert len(procs)==16
for row in procs:assert '--ordinary-congestion-scale=64'in row['command']and '--critical-first'in row['command']and '--resource-labels=8000000'in row['command']
r=json.loads((b/'r256-ordinary-cost-regression-511/directional-regression.json').read_text());assert r['passed']and len(r['ordinary_scale_cases'])==3 and len(r['rejected'])==26
metrics={};bindings={}
for seed in [4850,5120]:
 rounds={};progress=[]
 for p in(root/str(seed)/'route').glob('trial-*/router.log'):
  raw=p.read_bytes();bindings[str(p)]=dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),active_prefix_snapshot=True)
  events=[]
  for line in raw.decode().splitlines():
   try:d=json.loads(line)
   except ValueError:continue
   events.append(d)
   if 'conflict_nodes'in d:rounds.setdefault(d['round'],[]).append(d)
  if events:progress.append(events[-1])
 metrics[str(seed)]=dict(rounds={str(k):dict(observed_trials=len(v),mean_conflict_positions=statistics.mean(x['conflict_nodes']for x in v),mean_excess_occupancy=statistics.mean(x['excess_occupancy']for x in v))for k,v in rounds.items()},current_progress=progress)
out.mkdir();d=dict(passed=True,time=time.time(),whole_system_qualified=False,inputs=rows,actual_current_processes=procs,candidate_binary_sha256=sha(binary),candidate_cpp_sha256=sha(b/'source-510/project/experiments/control_v1/tree_router.cpp'),actual_regression_receipt_sha256=sha(b/'r256-ordinary-cost-regression-511/receipt.json'),actual_ordinary_cases=3,actual_rejected=26,metrics=metrics,log_prefix_bindings=bindings,scope='All16 actual453 placement4610/RNG4661/cost2/weight256/adaptive trial input bytes identical. Candidate5120 actual16 owned child processes all carry separate ordinary64 plus unchanged8million-label/critical flags. Queue source guard independently preserves original finite branch/resource header and nine final gates. Metrics are active prefix snapshots, no original round duration inferred. Source evolution plus exactly one optional search cost differs; no convergence, timing or physical qualification claim.');(out/'receipt.json').write_text(json.dumps(d,indent=2));print(json.dumps(dict(passed=True,inputs_equal=16,actual_processes=len(procs),metrics={k:v['rounds']for k,v in metrics.items()})))
'''
compile(q,'compare515','exec');print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],universal_newlines=True))
