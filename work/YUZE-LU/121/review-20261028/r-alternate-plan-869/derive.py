from pathlib import Path
from collections import defaultdict,Counter
import sys,json,hashlib
sys.path.insert(0,'project/experiments/block_v1')
from revision300_v_clearance_corners import intersect,outside_area
from revision300_v_via_batch import contains,pairs
b=Path('work/YUZE-LU/121/review-20261028');n=next((b/'r-851-neighborhood-858').rglob('revision300-r-current-neighborhood.json')).parent
meta=json.loads((n/'revision300-r-current-neighborhood.json').read_bytes());geometry=Path('.local/issue121/r851-neighborhood.tsv');routes_path=Path('.local/issue121/r857-observed-routes.json')
assert hashlib.sha256(geometry.read_bytes()).hexdigest()=='27973231cb99fb62205751fd275e62d1abc5c0ca290b589616f5ece414c3329d'
assert hashlib.sha256(routes_path.read_bytes()).hexdigest()=='4eac21628e0759893394c2d7585cef45e2f15cd06c68800d4ecbc819bb8d73e4'
routes=json.loads(routes_path.read_bytes());aliases={bytes.fromhex(v).decode().replace('\\',''):a for a,v in(line.split('\t')for line in(n/'net-aliases.tsv').read_text().splitlines())}
dimensions={l:(int(w),int(s))for l,w,s in(line.split('\t')for line in(n/'layer-dimensions.tsv').read_text().splitlines())};foot=defaultdict(list);shapes=defaultdict(list)
for line in(n/'via-footprints.tsv').read_text().splitlines():v,l,*box=line.split('\t');foot[v].append((l,list(map(int,box))))
for line in geometry.read_text().splitlines():
 if not line or line.startswith('#'):continue
 i,a,l,k,*box=line.split('\t');shapes[int(i)].append((a,l,k,list(map(int,box))))
corners=json.loads((b/'r-851-neighborhood-858/clearance-plan.json').read_bytes())['selected'];bad=set(json.loads((b/'verification-865.json').read_bytes())['excluded_modified_nets']);corners=[p for p in corners if p['net'].replace('\\','')not in bad]
via=json.loads((b/'r-857-topology-862/via-candidate-plan.json').read_bytes())['selected']
seen={p['net']for p in corners+via};extras=[(p['net'],p['layer'],p['bbox_dbu'])for p in corners]
for p in via:extras.append((p['net'],'metal2',p['conservative_m2_bbox_dbu']))
selected=[];skipped=[]
def qualify(i,name,a,bp,remove,keep,wires,bridge_layer,method):
 if any(v%10 for v in a+bp)or a==bp:return None
 own=aliases[name];half=dimensions[bridge_layer][0]//2
 bridge=[min(a[0],bp[0])-half,min(a[1],bp[1])-half,max(a[0],bp[0])+half,max(a[1],bp[1])+half]
 additions=[(bridge_layer,bridge)]+[(l,[x0+bp[0],y0+bp[1],x1+bp[0],y1+bp[1]])for l,(x0,y0,x1,y1)in foot[remove['via']]if l.startswith('metal')]
 removed=[(l,[x0+a[0],y0+a[1],x1+a[0],y1+a[1]])for l,(x0,y0,x1,y1)in foot[remove['via']]if l!=bridge_layer]
 context=shapes[i]+[(aliases[net],l,'other-proposed-addition',box)for net,l,box in extras]
 for l,box in additions:
  spacing=dimensions[l][1];wx0,wy0,wx1,wy1=meta['windows'][i]['bbox_dbu']
  if box[0]-spacing<wx0 or box[1]-spacing<wy0 or box[2]+spacing>wx1 or box[3]+spacing>wy1:return None
  ownboxes=[q for alias,layer,k,q in context if alias==own and layer==l and not k.endswith('obstruction')and not(k=='wire-via'and(layer,q)in removed)]
  for alias,layer,k,q in context:
   if alias==own or layer!=l:continue
   overlap=intersect(box,[q[0]-spacing,q[1]-spacing,q[2]+spacing,q[3]+spacing])
   if overlap and outside_area(ownboxes,overlap)>0:return None
 return dict(index=i,net=name,a=a,b=bp,removed_via=remove,retained_via=keep,moved_via=dict(layer=remove['layer'],points=[bp+[None]],via=remove['via']),preserved_source_wires=wires,retain_pad_layer=bridge_layer,added_bridge=dict(layer=bridge_layer,points=[a+[None],bp+[None]],via=None),new_shapes=additions,method=method)
for i,m in enumerate(meta['markers']):
 name=m['net'];layer=m['layer'];level=int(layer[5:]);paths=routes[name]['nonrect_paths'];own=aliases[name];options=[]
 if name in seen or i==583:continue
 row=dict(marker=m,same_net_nearby_rectangles=[dict(bbox_dbu=q,shape=k)for a,l,k,q in shapes[i]if a==own and l==layer])
 if layer=='metal3':
  for a,bp in pairs(row):
   a=list(a);bp=list(bp);wires=[p for p in paths if contains(p,layer,a,bp)]
   if not wires:continue
   for a,bp in [(a,bp),(bp,a)]:
    high=[p for p in paths if p['layer']=='metal3'and p['via']and len(p['points'])==1 and p['points'][0][:2]==a]
    low=[p for p in paths if p['layer']=='metal2'and p['via']and len(p['points'])==1 and p['points'][0][:2]==bp]
    if len(high)!=1 or len(low)!=1:continue
    p=qualify(i,name,a,bp,high[0],low[0],wires,'metal4','reverse-M4-pair')
    if p:options.append(p)
 for v in paths:
  if not v['via']or len(v['points'])!=1:continue
  sourcelevel=int(v['layer'][5:])
  if sourcelevel not in(level-1,level):continue
  a=v['points'][0][:2];mx0,my0,mx1,my1=m['bbox_dbu'];touches=False
  for l,(x0,y0,x1,y1)in foot[v['via']]:
   x0+=a[0];x1+=a[0];y0+=a[1];y1+=a[1]
   if l==layer:touches|=((x1==mx0 or x0==mx1)and y0<=my0 and y1>=my1)or((y1==my0 or y0==my1)and x0<=mx0 and x1>=mx1)
  if not touches:continue
  bridge_layer='metal'+str(level-1 if sourcelevel==level-1 else level+1)
  for leg in paths:
   if leg['layer']!=layer or leg['via']or len(leg['points'])!=2:continue
   points=[p[:2]for p in leg['points']]
   if a not in points:continue
   bp=points[1]if points[0]==a else points[0]
   if not 0<abs(a[0]-bp[0])+abs(a[1]-bp[1])<=2000:continue
   bends=[p for p in paths if p!=leg and contains(p,layer,bp,bp)and(p['points'][0][0]==p['points'][1][0])!=(leg['points'][0][0]==leg['points'][1][0])]
   if not bends or any(p['layer']==v['layer']and p['via']==v['via']and len(p['points'])==1 and p['points'][0][:2]==bp for p in paths):continue
   p=qualify(i,name,a,bp,v,None,[leg]+bends,bridge_layer,'move-via-to-existing-bend')
   if p:options.append(p)
 if options:
  p=options[0];selected.append(p);seen.add(name);extras.extend((name,l,q)for l,q in p['new_shapes'])
 else:skipped.append(i)
inputs={name:hashlib.sha256((n/name).read_bytes()).hexdigest()for name in ['revision300-r-current-neighborhood.json','via-footprints.tsv','net-aliases.tsv','layer-dimensions.tsv']}
d=dict(selected=selected,skipped=skipped,physical_qualified=False,source_native_count=584,source_receipt_sha256='759cae257ff6731b8424eac6270a7bf255b6f0dc980ba0ff3a7bb508037b916b',observed_sha256=hashlib.sha256(routes_path.read_bytes()).hexdigest(),geometry_sha256=hashlib.sha256(geometry.read_bytes()).hexdigest(),inputs_sha256=inputs,excluded_active_nets=len({p['net']for p in corners+via}),conservative_active_new_shapes=extras[:314+53],scope='Derived only. Current R851 complete geometry and R857 exact topology, all314 corner/53 M2 bridge proposals conservatively included; those nets excluded. One edit per remaining net, new additions considered sequentially. Foreign removed via pads retained conservatively; removed own pads excluded from coverage. Original adjacent-layer pad retained explicitly. No native check or final qualification; actual combined source must be rechecked.')
out=Path('project/experiments/block_v1/r-alternate-plan-869.json');assert not out.exists();out.write_bytes((json.dumps(d,indent=2)+'\n').encode())
print('869 derived',len(selected),'methods',Counter(p['method']for p in selected),'shards',Counter(int(hashlib.sha256(p['net'].encode()).hexdigest(),16)%6 for p in selected),'skipped',len(skipped))
