import pathlib,json,math,collections
P=pathlib.Path;root=P(__file__).resolve().parent
old=P('/public/home/yuzelu/project-circuit/issue287-route-ab-20261117')
Z={10:11.09,11:13.89,12:16.69}
inventory=json.loads(P('/public/home/yuzelu/project-circuit/issue287-route-ab-all-20261117/inventory.json').read_text());wanted={(j['scheme'],j['net']):j for j in inventory}
graphs={}
for label,path in [('A',old/'A-mapped.json'),('B',P('/public/home/yuzelu/project-circuit/side-top-pressure-20261117/route-fixed.json'))]:
 routes=json.loads(path.read_text())['routes'];lines=(old/('field-'+label)/'field.in').read_text().splitlines();pos=1;scene=[]
 for name in sorted(routes):
  nb,nn=map(int,lines[pos].split());pos+=1;boxes=lines[pos:pos+nb];pos+=nb+nn
  r=routes[name];edges=[]
  for s in r['segments']:
   layer=int(s['layer'][1:]);a=tuple(s['a']);b=tuple(s['b']);length=sum(abs(x-y) for x,y in zip(a,b))/2000
   if length:edges.append(((layer,*a),(layer,*b),length*.03/2))
  for via in r['via10']:a=tuple(via['at']);edges.append(((10,*a),(11,*a),.08))
  for via in r['via11']:a=tuple(via);edges.append(((11,*a),(12,*a),.08))
  nodes=[];res=[]
  def ix(v):
   if v not in nodes:nodes.append(v)
   return nodes.index(v)
  for a,b,R in edges:
   n=max(1,math.ceil(sum(abs(x-y) for x,y in zip(a[1:],b[1:]))/2000/50)) if a[0]==b[0] else 1
   chain=[(a[0],a[1]+(b[1]-a[1])*k/n,a[2]+(b[2]-a[2])*k/n) for k in range(n)]+[b]
   for u,v in zip(chain,chain[1:]):res.append((ix(u),ix(v),R/n))
  points=[(x/2000,y/2000,Z[l]) for l,x,y in nodes]
  if (label,name) in wanted:
   spec=wanted[label,name];ends={v['pin']:ix((10,*v['at'])) for v in r['via10']};assert len(points)==len(nodes)
   adjacency=collections.defaultdict(set)
   for a,b,R in res:adjacency[a].add(b);adjacency[b].add(a)
   seen=set();todo=[ends[spec['driver']]]
   while todo:
    a=todo.pop()
    if a in seen:continue
    seen.add(a);todo.extend(adjacency[a]-seen)
   assert len(seen)==len(nodes),(label,name,'disconnected centerline',len(seen),len(nodes))
   graphs[label+'-'+name]=dict(spec,nodes=points,resistors=res,source=ends[spec['driver']],sink=ends[spec['sinks'][0]],degree_max=max(map(len,adjacency.values())))
  else:points=[points[0],points[-1]]
  scene.append((boxes,points))
 with (root/('field-'+label+'.in')).open('w') as f:
  print(3.9,len(scene),file=f)
  for boxes,points in scene:
   print(len(boxes),len(points),file=f)
   for box in boxes:print(box,file=f)
   for point in points:print(*point,file=f)
(root/'graphs.json').write_text(json.dumps(graphs));assert len(graphs)==646
src=P('/public/home/yuzelu/PingyangHuang/issue-199-field-xXrAwSOn/project/experiments/m11_m12_rcx/field_row.cpp').read_text()
src=src[:src.index('    std::cout << std::setprecision')]
src=src.replace('argc != 6','argc != 7').replace('opts.gauss_offset = 0.25;','opts.gauss_offset = std::stod(argv[6]);').replace('    opts.capture_nodes = nodes;','').replace('    opts.capture_nodes[master].clear();','')
src+='''    std::cout << std::setprecision(17) << "{\\"master\\":" << master << ",\\"walks\\":" << row.walks << ",\\"total\\":" << row.cap[master] << ",\\"sigma\\":" << row.sigma[master] << ",\\"nodes\\":[";
    for(size_t i=0;i<row.partial_cap.size();++i) { if(i) std::cout << ','; std::cout << '[' << row.partial_cap[i][master] << ',' << row.partial_sigma[i][master] << ']'; }
    std::cout << "]}\\n";
  } catch(const std::exception& e) {std::cerr << e.what() << '\\n';return 1;}
}
'''
(root/'node_row.cpp').write_text(src)
print('646 graphs prepared; node-distribution qualification PENDING')
