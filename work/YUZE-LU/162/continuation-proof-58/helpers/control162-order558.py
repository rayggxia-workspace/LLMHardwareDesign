from pathlib import Path
import subprocess,shlex
q=r"""from pathlib import Path
import json,hashlib,subprocess,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');out=b/'r256-initial-order-window-diagnostic-558';assert not out.exists();out.mkdir();source=b/'source-537/project/experiments/control_v1/tree_router.cpp';text=source.read_text();needle=' vector<vector<vector<int>>>access(count),branches(count);';assert text.count(needle)==1
extra=r'''
 vector<int>diagnostic_order(count);iota(diagnostic_order.begin(),diagnostic_order.end(),0);mt19937 diagnostic_rng(seed);shuffle(diagnostic_order.begin(),diagnostic_order.end(),diagnostic_rng);
 if(initial_order){vector<int>span(count);for(int n=0;n<count;++n){int xlo=nx,xhi=0,ylo=ny,yhi=0;for(int v:ends[n]){auto c=coord(v);xlo=min(xlo,c[0]);xhi=max(xhi,c[0]);ylo=min(ylo,c[1]);yhi=max(yhi,c[1]);}span[n]=xhi-xlo+yhi-ylo;}
 stable_sort(diagnostic_order.begin(),diagnostic_order.end(),[&](int a,int b){if(initial_order==1)return span[a]<span[b];if(initial_order==2)return span[a]>span[b];return ends[a].size()>ends[b].size();});}
 stable_sort(diagnostic_order.begin(),diagnostic_order.end(),[&](int a,int b){return(a<locked_count)>(b<locked_count);});
 cout<<"{\"diagnostic_order\":[";for(int i=0;i<count;++i){if(i)cout<<',';cout<<'"'<<names[diagnostic_order[i]]<<'"';}cout<<"]}"<<endl;return 0;
'''
cpp=out/'order.cpp';cpp.write_text(text.replace(needle,extra+needle));sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
config=dict(source=str(source),source_sha256=sha(source),generated_sha256=sha(cpp),out=str(out),graph=str(b/'r256-composition-453/topology/boundary-graph.json'),candidates=[5400,5450,5451,5550,5551],root=str(b/'r256-composition-453/upper-candidates'));(out/'config.json').write_text(json.dumps(config))
run=r'''from pathlib import Path
import json,subprocess,hashlib,collections,time
o=Path(__import__('sys').argv[1]);c=json.loads((o/'config.json').read_text());s=Path(c['source']);cmd=['g++','-std=c++17','-O2','-I'+str(s.parent),str(o/'order.cpp'),'-o',str(o/'order')]
with(o/'compile.log').open('w')as f:subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,check=True)
r=dict(passed=False,whole_system_qualified=False,config=c,windows=[]);graph=json.loads(Path(c['graph']).read_text())
for seed in c['candidates']:
 p=Path(c['root'])/str(seed)/'route';inp=p/'trial-0/input.txt';log=p/'trial-0/router.log';events=[json.loads(x)for x in log.read_text().splitlines()if x.startswith('{')];progress=[x for x in events if'routed'in x];last=progress[-1];assert last['round']==0
 flags=['--resource-labels=8000000','--critical-first','--ordinary-congestion-scale='+('256'if seed==5450 else'64')]+(['--ordinary-search-margin=64']if seed==5451 else[])
 command=[str(o/'order'),str(inp),str(o/('not-a-route-'+str(seed)))]+flags;raw=subprocess.check_output(command);(o/('order-'+str(seed)+'.stdout')).write_bytes(raw);order=[json.loads(x)['diagnostic_order']for x in raw.decode().splitlines()if'diagnostic_order'in x][0];assert len(order)==11149 and len(set(order))==11149
 count=last['routed'];names=order[count:min(count+100,len(order))];roles=collections.Counter();lengths=[];rows={}
 for line in inp.read_text().splitlines()[1:]:
  a=line.split();n=int(a[1]);xy=[tuple(map(int,a[2+2*i:4+2*i]))for i in range(n)];rows[a[0]]=xy
 for name in names:
  if name.startswith('net_'):
   x=graph['connections'][name[4:]];role=x['driver']['instance']+'->'+','.join(sorted(set(e['instance']for e in x['sinks'])));roles[role]+=1
  else:roles[name]+=1
  xy=rows[name];lengths.append(4*(max(x for x,y in xy)-min(x for x,y in xy)+max(y for x,y in xy)-min(y for x,y in xy)))
 r['windows'].append(dict(candidate=seed,actual_input_sha256=hashlib.sha256(inp.read_bytes()).hexdigest(),actual_progress=last,next_at_most100_initial_order_names=names,roles=dict(roles),sum_hpwl_um=sum(lengths),maximum_hpwl_um=max(lengths)if lengths else None,scope='Only bounds next100 initial-order nets after last emitted100-net progress. Does not identify exact executing net or measure per-net search time.'))
r.update(passed=True,time=time.time(),scope='Software initial-order diagnostic on actual frozen source537 and real trial0 inputs. Original parser with early return before routing, exact stdshuffle/stable span-order/locked partition, same node5 compiler/container. No active router attachment, mutation, cancellation or physical output. Only first-round order; no speed or feasibility claim.');(o/'receipt.json').write_text(json.dumps(r,indent=2));print(json.dumps(dict(passed=True,windows=[dict(candidate=x['candidate'],progress=x['actual_progress'],roles=x['roles'],maximum_hpwl_um=x['maximum_hpwl_um'])for x in r['windows']])))
'''
(out/'run.py').write_text(run);job=subprocess.check_output(['scontrol','show','job','95155','-o'],universal_newlines=True);assert 'UserId=yuzelu(10011)'in job and'JobName=yzl-ctl162-'in job and'NodeList=node5 'in job
cmd=['srun','--jobid=95155','--overlap','-n1','-c1','/public/software/singularity-ce-4.3.4/bin/singularity','exec','--cleanenv','--bind','/public/home/yuzelu','/public/home/yuzelu/opt/eda/containers/orfs-current-repacked.sif','bash','-c','set -euo pipefail; source /OpenROAD-flow-scripts/env.sh; exec python3 "$@"','bash',str(out/'run.py'),str(out)];(out/'launch.json').write_text(json.dumps(dict(command=cmd,job_details=job,scope='Brief metadata compile/inspection sharing existing owned allocation; no extra parent or routing children.')))
with(out/'run.stdout').open('w')as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT)
assert r.returncode==0,(out/'run.stdout').read_text()[-2000:];print((out/'run.stdout').read_text())
"""
compile(q,'order558','exec');remote='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162/order558.py';p=Path(__file__).with_name('control162-order558-remote.py');p.write_bytes(q.encode());subprocess.run(['scp',str(p),'yuzelu@10.129.166.172:'+remote],check=True);print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 '+shlex.quote(remote)],universal_newlines=True))
