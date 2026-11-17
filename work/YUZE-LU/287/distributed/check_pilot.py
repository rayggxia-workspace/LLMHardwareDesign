import pathlib,json,heapq,math,os
p=pathlib.Path(__file__).resolve().parent;graphs=json.loads((p/'graphs.json').read_text());out={}
for key in ['A-n14653','A-n14598','B-n14653','B-n14598','B-G-S-22','B-G-S-33']:
 g=graphs[key];adj=[[] for _ in g['nodes']]
 for a,b,r in g['resistors']:adj[a].append((b,r));adj[b].append((a,r))
 dist=[math.inf]*len(adj);dist[g['source']]=0;todo=[(0,g['source'])]
 while todo:
  d,a=heapq.heappop(todo)
  if d!=dist[a]:continue
  for b,r in adj[a]:
   if d+r<dist[b]:dist[b]=d+r;heapq.heappush(todo,(d+r,b))
 rows={}
 for off in [.25,.125,.0625]:
  r=json.loads((p/(os.getenv('PROJECTION_PREFIX','')+key+'-'+str(off)+'.json')).read_text());nodes=r['nodes'];c=[v[0] for v in nodes]
  rows[str(off)]={'total_fF':r['total'],'sigma_fF':r['sigma'],'sum_nodes':sum(c),'negative_nodes':sum(x<0 for x in c),'negative_mass_fF':-sum(min(0,x) for x in c),'significant_negative_nodes':sum(x+3*s<0 for x,s in nodes),'elmore_wire_ns':sum(d*x for d,x in zip(dist,c))*1e-6,'min_node_fF':min(c)}
 out[key]={'nodes':len(adj),'tree':len(g['resistors'])==len(adj)-1,'degree':g['degree_max'],'offsets':rows,'moment_change_percent':100*(rows['0.0625']['elmore_wire_ns']/rows['0.125']['elmore_wire_ns']-1)}
(p/(os.getenv('PROJECTION_PREFIX','')+'pilot-check.json')).write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
