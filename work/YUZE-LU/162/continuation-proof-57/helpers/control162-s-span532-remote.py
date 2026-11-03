from pathlib import Path
import json,hashlib,time,statistics
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');out=b/'r256-s-pair-span-532';assert not out.exists();graph=b/'r256-composition-453/topology/boundary-graph.json';g=json.loads(graph.read_text());p=b/'r256-composition-453/upper-candidates/5120/route/trial-0/input.txt';sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest();pairs={}
for bit,c in g['connections'].items():
 ends=[c['driver'],*c['sinks']]
 if len(ends)==2 and{e['instance']for e in ends}=={'macro_s','s_port'}:pairs['net_'+bit]=ends
assert len(pairs)>=256;rows=[]
with p.open()as f:
 header=f.readline().split()
 for line in f:
  v=line.split()
  if v[0]not in pairs:continue
  assert int(v[1])==2;a=list(map(int,v[2:4]));c=list(map(int,v[4:6]));dx=abs(a[0]-c[0])*4;dy=abs(a[1]-c[1])*4;rows.append(dict(net=v[0],endpoints=pairs[v[0]],actual_grid_ends=[a,c],span_um=[dx,dy],manhattan_um=dx+dy))
assert len(rows)==len(pairs);out.mkdir();d=dict(passed=True,time=time.time(),whole_system_qualified=False,input_sha256={str(graph):sha(graph),str(p):sha(p)},actual_pair_net_count=len(rows),sum_pair_manhattan_um=sum(x['manhattan_um']for x in rows),mean_pair_manhattan_um=statistics.mean(x['manhattan_um']for x in rows),maximum_pair_manhattan_um=max(x['manhattan_um']for x in rows),rows=rows,scope='Readback of actual453 placement4610 actual trial input and exact graph S/s_port direct two-ended nets. Grid pitch4um, no path or timing result and no placement optimization performed on login. This geometric diagnosis motivates allocated-node placement compacting, does not prove global unroutability or qualify anything.');(out/'receipt.json').write_text(json.dumps(d,indent=2));print(json.dumps({k:d[k]for k in ['passed','actual_pair_net_count','sum_pair_manhattan_um','mean_pair_manhattan_um','maximum_pair_manhattan_um']}))
