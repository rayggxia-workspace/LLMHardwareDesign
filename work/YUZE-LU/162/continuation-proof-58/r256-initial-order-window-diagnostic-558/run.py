from pathlib import Path
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
