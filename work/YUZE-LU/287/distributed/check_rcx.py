import pathlib,json,re,collections,math
P=pathlib.Path;p=P(__file__).resolve().parent;graphs=json.loads((p/'graphs.json').read_text());out=[];extracted={}
for label in ['A','B']:
 maps={};mode=None;net=None
 for line in (p/('rcx-'+label)/'extracted.spef').open():
  a=line.split()
  if not a:continue
  if a[0]=='*NAME_MAP':mode='map';continue
  if a[0]=='*D_NET':net=maps.get(a[1],a[1]).replace('\\','');extracted[label+'-'+net]={'res':[],'ports':[]};mode=None
  elif a[0]=='*CONN':mode='conn'
  elif a[0]=='*RES':mode='res'
  elif a[0] in ['*CAP','*END']:mode=None
  elif mode=='map' and a[0][1:].isdigit():maps[a[0]]=a[1]
  elif mode=='res':extracted[label+'-'+net]['res'].append((a[1],a[2],float(a[3])))
  elif mode=='conn' and a[0] in ['*P','*I']:extracted[label+'-'+net]['ports'].append(a[1])
for label,path in [('A','/public/home/yuzelu/project-circuit/issue287-route-ab-20261117/A-mapped.json'),('B','/public/home/yuzelu/project-circuit/side-top-pressure-20261117/route-fixed.json')]:
 routes=json.loads(P(path).read_text())['routes']
 for name,r in routes.items():
  key=label+'-'+name
  if key not in graphs:continue
  g=graphs[key];new=[];i=0
  for seg in r['segments']:
   length=sum(abs(a-b) for a,b in zip(seg['a'],seg['b']))/2000
   if not length:continue
   n=max(1,math.ceil(length/50))
   for _ in range(n):
    a,b,R=g['resistors'][i];new.append((a,b,R+.03/n));i+=1
  new+=g['resistors'][i:]
  x=extracted[key];raw=sum(e[2] for e in x['res']);pred=sum(e[2] for e in new)
  adj=collections.defaultdict(set)
  for a,b,R in x['res']:adj[a].add(b);adj[b].add(a)
  seen=set();todo=x['ports'][:1]
  while todo:
   a=todo.pop()
   if a in seen:continue
   seen.add(a);todo.extend(adj[a]-seen)
  assert len(x['ports'])==2 and all(a in seen for a in x['ports']),key
  assert abs(raw-pred)<max(.002,raw*1e-5),(key,raw,pred)
  g['resistors']=new;g['rcx_sum_ohm']=raw
  out.append(dict(key=key,rcx_R_ohm=raw,reconstructed_R_ohm=pred,error_ohm=pred-raw,connected=True))
assert len(out)==646
(p/'graphs-rcx.json').write_text(json.dumps(graphs));(p/'rcx-validation.json').write_text(json.dumps(out,indent=2));print('646/646 RCX R sums and two-port connectivity verified')
