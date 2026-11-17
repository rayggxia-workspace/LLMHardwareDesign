import pathlib,json,heapq,math
P=pathlib.Path;p=P(__file__).resolve().parent;graphs=json.loads((p/'graphs-rcx.json').read_text());baseline=P('/public/home/yuzelu/project-circuit/issue287-route-ab-all-20261117');results=[];caps={}
for key,g in graphs.items():
 old=json.loads((baseline/(key+'.summary.json')).read_text());target=old['self_fF'];adj=[[] for _ in g['nodes']]
 for a,b,R in g['resistors']:adj[a].append((b,R));adj[b].append((a,R))
 dist=[math.inf]*len(adj);dist[g['source']]=0;todo=[(0,g['source'])]
 while todo:
  d,a=heapq.heappop(todo)
  if d!=dist[a]:continue
  for b,R in adj[a]:
   if d+R<dist[b]:dist[b]=d+R;heapq.heappush(todo,(d+R,b))
 assert len(g['resistors'])==len(adj)-1 and max(map(len,adj))==2,key
 variants=[]
 for off in [.125,.0625]:
  r=json.loads((p/'all-nodes'/(key+'-'+str(off)+'.json')).read_text());v=[n[0] for n in r['nodes']];assert len(v)==len(adj)
  assert abs(sum(v)-r['total'])<1e-7
  z=abs(r['total']-target)/math.hypot(r['sigma'],old['sigma_fF'])
  norm=[x*target/sum(v) for x in v];moment=sum(d*c for d,c in zip(dist,norm))*1e-6
  variants.append(dict(offset=off,total_fF=r['total'],z_to_original=z,min_node_fF=min(v),negative_nodes=sum(x<0 for x in v),negative_mass_fF=-sum(min(0,x) for x in v),moment_ns=moment,normalized_cap_fF=norm))
 diff=abs(variants[0]['moment_ns']-variants[1]['moment_ns']);tol=max(.0002,.01*variants[0]['moment_ns'])
 passed=all(v['negative_nodes']==0 and v['z_to_original']<=5 for v in variants) and diff<=tol
 results.append(dict(key=key,passed=passed,moment_delta_ns=diff,tolerance_ns=tol,variants=[{k:v for k,v in r.items() if k!='normalized_cap_fF'} for r in variants]))
 caps[key]=variants[0]['normalized_cap_fF']
out=dict(count=len(results),passed=all(r['passed'] for r in results),failed=[r for r in results if not r['passed']],max_moment_delta_ns=max(r['moment_delta_ns'] for r in results),results=results)
(p/'node-validation.json').write_text(json.dumps(out,indent=2));(p/'node-capacitances.json').write_text(json.dumps(caps));print(json.dumps({k:v for k,v in out.items() if k!='results'},indent=2))
