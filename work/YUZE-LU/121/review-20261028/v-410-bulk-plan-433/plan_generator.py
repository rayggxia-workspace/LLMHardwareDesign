from pathlib import Path
import json,re,sys,copy,collections,gzip,base64
from decimal import Decimal
sys.path.insert(0,'project/experiments/block_v1')
from native_escape import parse,signature,on_segment,path_length
base=Path('work/YUZE-LU/121/review-20261028');folder=base/'v-410-all-marker-def-432';index=json.loads((folder/'index.json').read_bytes());archive=json.loads(gzip.decompress((folder/index['archive']['path']).read_bytes()));texts={v['net']:base64.b64decode(archive[v['net']]).decode()for v in index['members'].values()};original={n:parse(t)for n,t in texts.items()};current={n:copy.deepcopy(p[1])for n,p in original.items()};plans=[];rejected=[]
report=(base/'v-411-native-drc-snapshot/block-v1-20261030-411/tasks/revision300-drc-v/native-whole-drc.rpt').read_text()
def moved(paths,layer,vertices,delta,axis,via_move=None):
 result=copy.deepcopy(paths)
 for i,p in enumerate(paths):
  if p['layer']!=layer:continue
  if p['via']:
   if p['points'][0][:2]in vertices:
    assert via_move==p['via'],'Via anchor would move'
   else:continue
  else:
   for v in vertices:
    if on_segment(v,p):assert v in [x[:2]for x in p['points']],'Interior anchor would move'
  for j,point in enumerate(p['points']):
   if point[:2]in vertices:
    assert point[2]is None,'Explicit extension would move';q=list(point);q[axis]+=delta;result[i]['points'][j]=tuple(q)
 for p in result:
  if p['via']:continue
  a,b=p['points'];assert a[:2]!=b[:2]and(a[0]==b[0]or a[1]==b[1]),'Diagonal or collapsed path'
 return result
def shift_cluster(paths,start,axis,delta):
 # Propagate coordinate equality along perpendicular segments and vias.
 adjacency=collections.defaultdict(set)
 def edge(a,b):adjacency[a].add(b);adjacency[b].add(a)
 for p in paths:
  layer=int(p['layer'][5:]);a=p['points'][0][:2];node=(layer,*a)
  if p['via']:edge(node,(layer+1,*a))
  else:
   b=p['points'][1][:2]
   if a[axis]==b[axis]:edge(node,(layer,*b))
 selected=set();todo=[start]
 while todo:
  node=todo.pop()
  if node in selected:continue
  selected.add(node);todo.extend(adjacency[node]-selected)
 assert all(n[0]in (2,3,4)for n in selected),'Cluster reaches fixed other-layer anchor'
 result=copy.deepcopy(paths)
 for i,p in enumerate(paths):
  layer=int(p['layer'][5:])
  for v in selected:
   if layer==v[0]and not p['via']and on_segment(v[1:],p):assert v[1:]in [q[:2]for q in p['points']],'Interior anchor would move'
  for j,point in enumerate(p['points']):
   if(layer,*point[:2])in selected:
    assert point[2]is None,'Explicit extension would move';q=list(point);q[axis]+=delta;result[i]['points'][j]=tuple(q)
 for p in result:
  if p['via']:continue
  a,b=p['points'];assert a[:2]!=b[:2]and(a[0]==b[0]or a[1]==b[1]),'Diagonal or collapsed path'
 return result,selected
for number,r in enumerate(report.split('violation type: ')[1:]):
 names=re.findall(r'net:([^\s]+)',r);m=re.search(r'bbox = \(([^,]+), ([^)]+)\) - \(([^,]+), ([^)]+)\) on Layer (\w+)',r);x,y,X,Y=[int(Decimal(v)*2000)for v in m.groups()[:4]];layer=m[5]
 if layer=='metal9':continue
 n=names[0];assert len(names)==1;p=current[n]
 try:
  if layer=='metal2':
   assert X-x==140 and 0<Y-y<140,'Unsupported M2 marker dimensions';xm=(x+X)//2;matches=[]
   for direction,cy,hy in [(1,y-140,Y+70),(-1,Y+140,y-70)]:
    anchors=[a for a in p if a['via']and a['layer']in ('metal1','metal2')and a['points'][0][:2]==(xm,cy)]
    if not anchors:continue
    for a in p:
     if a['layer']==layer and not a['via']and a['points'][0][1]==a['points'][1][1]==hy and(xm,hy)in [q[:2]for q in a['points']]:matches.append((direction,a))
   assert len(matches)==1,'No unique via-and-free-bend pattern';direction,a=matches[0];vertices={q[:2]for q in a['points']};delta=direction*(140-(Y-y));result=moved(p,layer,vertices,delta,1)
   assert signature([a for a in p if a['layer']!=layer or a['via']])==signature([a for a in result if a['layer']!=layer or a['via']])
  else:
   assert layer=='metal3'and Y-y==140 and 0<X-x<140,'Unsupported M3 marker dimensions';ym=(y+Y)//2;left=(x-140,ym);right=(X+140,ym)
   for v in (left,right):assert any(a['via']and a['layer']in ('metal2','metal3')and a['points'][0][:2]==v for a in p),'Expected via anchor absent'
   assert any(a['layer']=='metal3'and not a['via']and on_segment(left,a)and on_segment(right,a)for a in p),'No common M3 bridge'
   delta=140-(X-x)
   try:result,selected=shift_cluster(p,(3,*right),0,delta)
   except AssertionError:delta=-delta;result,selected=shift_cluster(p,(3,*left),0,delta)
   vertices=sorted(selected)
   assert signature([a for a in p if a['layer']not in ('metal2','metal3','metal4')])==signature([a for a in result if a['layer']not in ('metal2','metal3','metal4')])
  assert [a['via']for a in p]==[a['via']for a in result]
  assert all(q[0]%10==0 and q[1]%10==0 for a in result for q in a['points'])
  current[n]=result;plans.append(dict(marker=number,net=n,layer=layer,delta=delta,vertices=sorted(vertices),changed_paths=sum(a!=b for a,b in zip(p,result))))
 except AssertionError as e:rejected.append(dict(marker=number,net=n,layer=layer,reason=str(e)))
print('proposed',len(plans),'nets',len({r['net']for r in plans}),'bylayer',collections.Counter(r['layer']for r in plans),'rejected',len(rejected),collections.Counter(r['reason']for r in rejected))
Path('.local/issue121/spacing433c-plan.json').write_text(json.dumps(dict(plans=plans,rejected=rejected,nets={n:dict(header=original[n][0],original_paths=original[n][1],final_paths=p)for n,p in current.items()if signature(p)!=signature(original[n][1])}),indent=2)+'\n')
