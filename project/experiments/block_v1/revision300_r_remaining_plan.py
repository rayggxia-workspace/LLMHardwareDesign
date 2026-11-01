from pathlib import Path
from collections import Counter,defaultdict
import hashlib,json,sys
sys.path.insert(0,'project/experiments/block_v1')
from revision300_v_clearance_corners import generate,intersect,outside_area
from revision300_v_via_batch import contains,pairs
from revision300_v_via_bridge import path_key
b=Path('work/YUZE-LU/121/review-20261028');n=b/'r-880-neighborhood-892';top=b/'r-889-topology-891'
meta=json.loads((n/'revision300-r-current-neighborhood.json').read_bytes());tr=json.loads((top/'revision300-r-composed-topology.json').read_bytes());routes=json.loads((top/'observed-routes.json').read_bytes())
assert meta['passed']and tr['passed']and meta['source_native_count']==tr['source_native_count']==55 and meta['source_receipt_sha256']==tr['source_receipt_sha256']=='4054eef392ce7c7a966b3774d51eb39d27540d88f6f7f52196692f520eac6938'
aliases={bytes.fromhex(v).decode().replace('\\',''):a for a,v in(line.split('\t')for line in(n/'net-aliases.tsv').read_text().splitlines())};dimensions={l:(int(w),int(s))for l,w,s in(line.split('\t')for line in(n/'layer-dimensions.tsv').read_text().splitlines())};shapes=defaultdict(list);foot=defaultdict(list)
for line in(n/'via-footprints.tsv').read_text().splitlines():v,l,*box=line.split('\t');foot[v].append((l,list(map(int,box))))
for line in(n/'neighborhood.tsv').read_text().splitlines():
 if not line or line.startswith('#'):continue
 i,a,l,k,*box=line.split('\t');shapes[int(i)].append((a,l,k,list(map(int,box))))
corners=generate(meta,n/'neighborhood.tsv',n/'net-aliases.tsv',n/'layer-dimensions.tsv');options=defaultdict(list);seen=defaultdict(set)
def clear(i,name,added,removed,extras=()):
 own=aliases[name];context=shapes[i]+[(aliases[net],l,'other-proposed-addition',box)for net,l,box in extras]
 for l,box in added:
  spacing=dimensions[l][1];wx0,wy0,wx1,wy1=meta['windows'][i]['bbox_dbu']
  if box[0]-spacing<wx0 or box[1]-spacing<wy0 or box[2]+spacing>wx1 or box[3]+spacing>wy1:return False
  known=[q for a,layer,k,q in context if a==own and layer==l and not k.endswith('obstruction')and not(k=='wire-via'and(layer,q)in removed)]
  for a,layer,k,q in context:
   if a==own or layer!=l:continue
   overlap=intersect(box,[q[0]-spacing,q[1]-spacing,q[2]+spacing,q[3]+spacing])
   if overlap and outside_area(known,overlap)>0:return False
 return True
def add(edit):
 name=edit['net'];key=json.dumps([edit['remove_paths'],edit['add_paths'],edit['add_rectangles']],sort_keys=True)
 if key in seen[name]:return
 if any(v%10 for l,*box in edit['add_rectangles']for v in box):return
 if any(x%10 or y%10 for p in edit['add_paths']for x,y,_ in p['points']):return
 paths=routes[name]['nonrect_paths'];before=Counter(map(path_key,paths))
 if any(before[path_key(p)]!=1 for p in edit['remove_paths'])or any(before[path_key(p)]for p in edit['add_paths']):return
 if not clear(edit['index'],name,edit['new_shapes'],edit['removed_coverage']):return
 seen[name].add(key);options[name].append(edit)
ns=b/'r-880-native-885/tasks/revision300-r-ns-wide-0';nsr=json.loads((ns/'receipt.json').read_bytes());nsd=json.loads((ns/'revision300-r-clearance-corners.json').read_bytes());assert nsr['passed']and nsd['passed']and nsd['added_markers']==0 and nsd['removed_markers']==2
patch=json.loads((ns/'selected-corners.json').read_bytes());assert len(patch)==1 and patch[0]['bbox_dbu']==[3712660,1580530,3712860,1580670]
ni=[i for i,m in enumerate(meta['markers'])if m['net']=='net131530'];assert len(ni)==2
add(dict(index=ni[-1],indices=ni,net='net131530',method='actual-passed-wideNS0',remove_paths=[],add_paths=[],add_rectangles=[['metal2']+patch[0]['bbox_dbu']],preserved_source_wires=[],new_shapes=[['metal2',patch[0]['bbox_dbu']]],removed_coverage=[]))
for p in corners['selected']:
 if p['net']=='net131530':continue
 add(dict(index=p['index'],indices=[p['index']],net=p['net'],method='fresh-current-corner',remove_paths=[],add_paths=[],add_rectangles=[[p['layer']]+p['bbox_dbu']],preserved_source_wires=[],new_shapes=[[p['layer'],p['bbox_dbu']]],removed_coverage=[]))
def via_edit(i,name,a,bp,av,keep,wires,delete,method):
 level=int(meta['markers'][i]['layer'][5:]);bottom=int(av['layer'][5:]);bridge_layer='metal'+str(level+1 if bottom==level else level-1)
 if bridge_layer not in dimensions:return
 half=dimensions[bridge_layer][0]//2;bridge=dict(layer=bridge_layer,points=[a+[None],bp+[None]],via=None)
 moving=None if delete else dict(layer=av['layer'],points=[bp+[None]],via=av['via'])
 added=[bridge]+([moving]if moving else[]);rects=[];newshapes=[(bridge_layer,[min(a[0],bp[0])-half,min(a[1],bp[1])-half,max(a[0],bp[0])+half,max(a[1],bp[1])+half])]
 removed=[]
 for l,(x0,y0,x1,y1)in foot[av['via']]:
  box=[x0+a[0],y0+a[1],x1+a[0],y1+a[1]]
  if l==bridge_layer:
   row=[l]+box
   if row not in routes[name]['rectangles']:rects.append(row)
   newshapes.append((l,box))
  else:removed.append((l,box))
  if moving and l.startswith('metal'):newshapes.append((l,[x0+bp[0],y0+bp[1],x1+bp[0],y1+bp[1]]))
 add(dict(index=i,indices=[i],net=name,method=method,remove_paths=[av],add_paths=added,add_rectangles=rects,preserved_source_wires=wires,retained_via=keep,new_shapes=newshapes,removed_coverage=removed))
for i,m in enumerate(meta['markers']):
 name=m['net'];layer=m['layer'];level=int(layer[5:]);paths=routes[name]['nonrect_paths'];own=aliases[name]
 if name=='net131530':continue
 row=dict(marker=m,same_net_nearby_rectangles=[dict(bbox_dbu=q,shape=k)for a,l,k,q in shapes[i]if a==own and l==layer])
 for aa,bb in pairs(row):
  aa=list(aa);bb=list(bb);wires=[p for p in paths if contains(p,layer,aa,bb)]
  if not wires:continue
  for a,bp in [(aa,bb),(bb,aa)]:
   av=[p for p in paths if p['via']and len(p['points'])==1 and p['points'][0][:2]==a and int(p['layer'][5:])in(level-1,level)]
   bv=[p for p in paths if p['via']and len(p['points'])==1 and p['points'][0][:2]==bp and int(p['layer'][5:])in(level-1,level)]
   for v in av:
    for keep in bv:
     delete=v['via']==keep['via']and v['layer']==keep['layer']
     via_edit(i,name,a,bp,v,keep,wires,delete,'same-via-pair-delete'if delete else'mixed-via-pair-move')
 mx0,my0,mx1,my1=m['bbox_dbu']
 for v in paths:
  if not v['via']or len(v['points'])!=1 or int(v['layer'][5:])not in(level-1,level):continue
  a=v['points'][0][:2];touches=False
  for l,(x0,y0,x1,y1)in foot[v['via']]:
   x0+=a[0];x1+=a[0];y0+=a[1];y1+=a[1]
   if l==layer:touches|=((x1==mx0 or x0==mx1)and y0<=my0 and y1>=my1)or((y1==my0 or y0==my1)and x0<=mx0 and x1>=mx1)
  if not touches:continue
  for wire in paths:
   if not contains(wire,layer,a,a):continue
   u,w=[p[:2]for p in wire['points']];horizontal=u[1]==w[1];points=[u,w]
   for offset in [140,-140,280,-280,380,-380,560,-560,70,-70,190,-190,420,-420,760,-760]:points.append([a[0]+offset,a[1]]if horizontal else[a[0],a[1]+offset])
   for bp in points:
    if bp==a or not contains(wire,layer,a,bp)or not 0<abs(a[0]-bp[0])+abs(a[1]-bp[1])<=2000:continue
    via_edit(i,name,a,bp,v,None,[wire],False,'move-via-on-preserved-source-wire')
variants=[]
for variant in range(6):
 selected=[];extras=[];skipped=[]
 for name,choices in options.items():
  if variant>=len(choices):continue
  p=choices[variant]
  if clear(p['index'],name,p['new_shapes'],p['removed_coverage'],extras):selected.append(p);extras.extend((name,l,q)for l,q in p['new_shapes'])
  else:skipped.append(name)
 assert selected,'No empty/duplicated filler variant'
 variants.append(dict(variant=variant,selected=selected,conflicting_nets_skipped=skipped))
for x in variants:
 assert len({p['net']for p in x['selected']})==len(x['selected'])
inputs={}
for folder,names in [(n,['receipt.json','revision300-r-current-neighborhood.json','neighborhood.tsv','net-aliases.tsv','layer-dimensions.tsv','via-footprints.tsv']),(top,['receipt.json','revision300-r-composed-topology.json','observed-routes.json']),(ns,['receipt.json','revision300-r-clearance-corners.json','selected-corners.json'])]:
 for name in names:inputs[(folder/name).as_posix()]=hashlib.sha256((folder/name).read_bytes()).hexdigest()
plan=dict(source_native_count=55,source_receipt_sha256=meta['source_receipt_sha256'],inputs_sha256=inputs,variants=variants,option_counts={name:len(v)for name,v in options.items()},unmatched_nets=sorted(set(routes)-set(options)),physical_qualified=False,scope='Derived only from actual88055 geometry plus actual88954-net routes,523 original RECTs retained. Six distinct finite per-net alternatives, scalar foreign/OBS and all-layer via-footprint pruning, conservative own removed pad coverage, current window and10DBU grid. Pair-delete, mixed via-stack move and finite along-existing-wire moves retain complete source wires and old adjacent pad. Known passedNS0 included only once. Each variant prunes mutual new-area conflicts; whole native/DEF/fullsignal and all final gates remain mandatory. No RTL, bitwidth or boundary change.')
out=Path('project/experiments/block_v1/r-remaining-plan-893.json');assert not out.exists();out.write_bytes((json.dumps(plan,indent=2)+'\n').encode());print('893 option nets',len(options),'unmatched',plan['unmatched_nets'],'variants',[len(v['selected'])for v in variants],'methods',[dict(Counter(p['method']for p in v['selected']))for v in variants])
