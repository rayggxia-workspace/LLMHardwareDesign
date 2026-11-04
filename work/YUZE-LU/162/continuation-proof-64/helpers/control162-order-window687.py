from pathlib import Path
import json,hashlib,subprocess,shlex,concurrent.futures,collections,time
h=Path(__file__).parent;out=h/'control162-order-window687';assert not out.exists();b='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162';host='yuzelu@10.129.166.172'
q=r'''from pathlib import Path
import json,hashlib
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();old=(b/'source-537/project/experiments/control_v1/tree_router.cpp').read_text();new=(b/'source-633/project/experiments/control_v1/tree_router.cpp').read_text();start=' vector<vector<int>>trees(count)';end=' bool complete=false';a=old.split(start,1)[1].split(end,1)[0];z=new.split(start,1)[1].split(end,1)[0];assert a==z
base=b/'r256-composition-453/upper-candidates/5400/route/trial-0/input.txt';header,body=base.read_bytes().split(b'\n',1);checks=[]
for seed in [6360,6720]:
 p=b/('r256-composition-453/upper-candidates/'+str(seed)+'/route/trial-0/input.txt');a,z=p.read_bytes().split(b'\n',1);x=header.split();y=a.split();assert z==body and all(x[i]==y[i]for i in [0,1,2,3,4,6,12]);checks.append(dict(seed=seed,input_sha256=sha(p),same_body_and_initial_order_header=True))
order=b/'r256-initial-order-window-diagnostic-558/order-5400.stdout';assert json.loads((order.parent/'receipt.json').read_text())['passed'];print(json.dumps(dict(passed=True,source_initial_order_bytes_exact=True,initial_order_source_sha256=hashlib.sha256(a.encode()if isinstance(a,str)else a).hexdigest(),baseline_input_sha256=sha(base),order_stdout_sha256=sha(order),inputs=checks)))
'''
compile(q,'remote-static-order-check687','exec');r=json.loads(subprocess.check_output(['ssh',host,'python3 -c '+shlex.quote(q)],timeout=20));out.mkdir();(out/'source-and-input-readback.json').write_bytes((json.dumps(r,indent=2)+'\n').encode())
items={'order-5400.stdout':b+'/r256-initial-order-window-diagnostic-558/order-5400.stdout'}
for seed in [6360,6720]:
 for name in ['input.txt','router.log']:items[str(seed)+'-'+name]=b+'/r256-composition-453/upper-candidates/'+str(seed)+'/route/trial-0/'+name
def copy(item):
 name,remote=item;subprocess.run(['scp','-o','ConnectTimeout=15',host+':'+remote,str(out/name)],check=True,stdout=subprocess.DEVNULL,timeout=30)
with concurrent.futures.ThreadPoolExecutor(max_workers=4)as ex:list(ex.map(copy,items.items()))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();assert sha(out/'order-5400.stdout')==r['order_stdout_sha256'];order=next(json.loads(x)['diagnostic_order']for x in (out/'order-5400.stdout').read_text().splitlines()if'diagnostic_order'in x);assert len(order)==len(set(order))==11149
graph=h/'LLMHardwareDesign-worktrees/issue-162-control/work/YUZE-LU/162/continuation-proof-54/r256-composition-453/topology/boundary-graph.json';assert sha(graph)=='49ba0e348f3583f6facdf60e771fe6f1329b46fe5aac872c3828d4b61ddb1a68';g=json.loads(graph.read_text(encoding='utf-8'));windows=[]
for seed in [6360,6720]:
 inp=out/(str(seed)+'-input.txt');assert sha(inp)==next(x['input_sha256']for x in r['inputs']if x['seed']==seed);events=[]
 for line in(out/(str(seed)+'-router.log')).read_text().splitlines():
  try:d=json.loads(line)
  except ValueError:continue
  if'routed'in d:events.append(d)
 last=events[-1];assert last['round']==0;names=order[last['routed']:last['routed']+100];roles=collections.Counter()
 for name in names:
  if name.startswith('net_'):
   x=g['connections'][name[4:]];roles[x['driver']['instance']+'->'+','.join(sorted(set(z['instance']for z in x['sinks'])))]+=1
  else:roles[name]+=1
 windows.append(dict(seed=seed,actual_trial=0,actual_progress=last,next_at_most100_names=names,roles=dict(roles)))
result=dict(passed=True,time=time.time(),whole_system_qualified=False,windows=windows,files=[dict(relative=n,path=p,sha256=sha(out/n),bytes=(out/n).stat().st_size)for n,p in items.items()],scope='Static initial-order source bytes and actual input/body/order-sensitive fields matched to existing558 complete stdshuffle/stable-span/priority order. Actual copied trial0 progress bounds next100 possible networks only; no exact active net/per-net duration, no active attachment/change, no new route or physical acceptance. Local analysis only; login performs source/input byte comparisons and existing file reads.')
(out/'receipt.json').write_bytes((json.dumps(result,indent=2)+'\n').encode());print(json.dumps(dict(passed=True,windows=[dict(seed=x['seed'],progress=x['actual_progress'],roles=x['roles'])for x in windows])))
