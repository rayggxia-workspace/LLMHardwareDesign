"""Map current foundry antenna polygons to physical parent DEF metal, retaining ambiguity."""
import pya,json,re,collections,hashlib,os,xml.etree.ElementTree as E
from pathlib import Path
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117')
out=Path(os.environ['U_ANT_OUT']).resolve();report=Path(os.environ['U_ANT_REPORT']).resolve();candidate=Path(os.environ['U_ANT_CANDIDATE']).resolve()
assert all(str(p).startswith(str(root)+'/') for p in (out,report,candidate))
path=candidate/'flow/results/nangate45/u-overlay-current/base/6_final.def'
scale=5; dbu=.0001; rows=[];regions=[]
for i,item in enumerate(E.parse(str(report)).findall('.//items/item')):
 cat=item.findtext('category');cell=item.findtext('cell');assert 'ANTENNA' in cat
 assert cell=='u_n32_controlled_dma_64',('nonparent antenna needs hierarchy transform',cell)
 shapes=[v.text for v in item.findall('values/value') if v.text.startswith('polygon: ')]
 assert shapes
 region=pya.Region()
 for geom in shapes:region.insert(pya.DPolygon.from_s(geom[9:]).to_itype(dbu))
 b=region.bbox();rows.append(dict(id=i,category=cat,layer=cat.split('_')[0].lower(),bbox_dbu=[b.left,b.bottom,b.right,b.top],geometry=shapes,hits=[]));regions.append(region)
grid=collections.defaultdict(set);pitch=100000
for i,m in enumerate(rows):
 a,b,c,d=m['bbox_dbu']
 for x in range(a//pitch,c//pitch+1):
  for y in range(b//pitch,d//pitch+1):grid[m['layer'],x,y].add(i)
def add(net,layer,box,kind):
 if not layer.startswith('metal'):return
 box=[v*scale for v in box];a,b,c,d=box;ids=set()
 for x in range(a//pitch,c//pitch+1):
  for y in range(b//pitch,d//pitch+1):ids.update(grid.get((layer,x,y),()))
 for i in ids:
  overlap=regions[i]&pya.Region(pya.Box(*box))
  if overlap.is_empty():continue
  area=overlap.area()*dbu*dbu
  rows[i]['hits'].append(dict(net=net,kind=kind,area_um2=area,box_dbu=box))
width={n:int(w) for n,w in (s.split('\t') for s in (out/'layers.tsv').read_text().splitlines())};vias=collections.defaultdict(list)
for line in (out/'vias.tsv').read_text().splitlines():
 name,layer,*box=line.split('\t');vias[name].append((layer,list(map(int,box))))
for line in (out/'bpins.tsv').read_text().splitlines():
 port,net,layer,*box=line.split('\t');add(net,layer,list(map(int,box)),'BPin:'+port)
deftext=path.read_text();ndrs={}
section=re.search(r'\nNONDEFAULTRULES\s+\d+\s*;(.*?)\nEND NONDEFAULTRULES',deftext,re.S)
if section:
 for match in re.finditer(r'^\s*-\s+(\S+)\s+(.*?);\s*$',section[1],re.M|re.S):
  name,body=match.groups();assert re.fullmatch(r'i289_upper_v2_(m9|m9m10)_(1000|1200|1400)',name),('Unreviewed NDR',name)
  layers=re.findall(r'\+\s+LAYER\s+(\S+)\s+WIDTH\s+(\d+)\s+SPACING\s+(\d+)',body)
  assert layers
  for layer,w,space in layers:assert int(w)==width[layer] and int(space)>0,('Non-native width or zero-gap NDR',name,layer,w,space)
  ndrs[name]={l:dict(width=int(w),spacing=int(sp)) for l,w,sp in layers}
s=deftext.split('\nNETS ',1)[1].split('\nEND NETS',1)[0];unknown=set();nsegments=0

for entry in re.finditer(r'^\s*-\s+(\S+)\s+(.*?);\s*$',s,re.M|re.S):
 net,body=entry.groups()
 assigned=re.findall(r'\+\s+NONDEFAULTRULE\s+(\S+)',body);assert len(assigned)<=1 and all(n in ndrs for n in assigned),(net,assigned)
 for route in re.finditer(r'(?:\+ ROUTED|\bNEW)\s+(\S+)\s+(.*?)(?=\bNEW|$)',body,re.S):
  layer,seq=route.groups();previous=None;prevext=None
  for token in re.finditer(r'\(\s*([*+-]?\d*|\*)\s+([*+-]?\d*|\*)(?:\s+(-?\d+))?\s*\)|(\S+)',seq):
   x,y,ext,name=token.groups()
   if x is not None:
    assert x and y
    point=(previous[0] if x=='*' else int(x),previous[1] if y=='*' else int(y));half=width[layer]//2;currext=half if ext is None else int(ext)
    if previous:
     assert point[0]==previous[0] or point[1]==previous[1]
     if point[0]==previous[0]:
      lo,hi=sorted([(previous[1],prevext),(point[1],currext)]);box=[point[0]-half,lo[0]-lo[1],point[0]+half,hi[0]+hi[1]]
     else:
      lo,hi=sorted([(previous[0],prevext),(point[0],currext)]);box=[lo[0]-lo[1],point[1]-half,hi[0]+hi[1],point[1]+half]
     add(net,layer,box,'wire');nsegments+=1
    previous=point;prevext=currext
   elif name in vias:
    assert previous
    for vl,box in vias[name]:add(net,vl,[v+previous[i%2] for i,v in enumerate(box)],'via:'+name)
   elif name=='NONDEFAULTRULE' or name in ndrs:
    assert assigned and (name=='NONDEFAULTRULE' or name==assigned[0]),(net,name)
   elif name=='TAPER':
    assert assigned,(net,'TAPER without NDR')
   elif name not in {'+','USE','SIGNAL','CLOCK'} and not name.isdigit():unknown.add(name)
assert not unknown,sorted(unknown)
endpoints=collections.defaultdict(list)
for line in (out/'endpoints.tsv').read_text().splitlines():
 net,inst,master,pin,direction,x,y,orient,w,h=line.replace('\\t','\t').split('\t');endpoints[net].append(dict(instance=inst,master=master,pin=pin,direction=direction,x=int(x),y=int(y),orient=orient,width=int(w),height=int(h)))
plans={};ambiguous=[];unmapped=[]
for m in rows:
 nets=sorted({h['net'] for h in m['hits']});m['nets']=nets
 if not nets:unmapped.append(m['id']);continue
 if len(nets)!=1:ambiguous.append(dict(id=m['id'],nets=nets));continue
 net=nets[0]
 if net not in plans:
  ep=endpoints[net];existing=[e for e in ep if e['master']=='ANTENNA_X1'];anchors=[e for e in ep if re.search(r'_X\d+$',e['master']) and e['master']!='ANTENNA_X1']
  anchors.sort(key=lambda e:(e['direction']!='INPUT',e['instance'],e['pin']));assert anchors,net
  plans[net]=dict(net=net,markers=[],existing_diodes=existing,anchor=anchors[0],all_standard_endpoints=anchors)
 plans[net]['markers'].append(m['id'])
r=dict(scope='Exact antenna polygon intersection with DEF metal rectangles and actual via enclosures; ambiguity fails mapping, final GDS still authoritative',def_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),antenna_report_sha256=hashlib.sha256(report.read_bytes()).hexdigest(),dbu_um=dbu,markers=rows,plans=list(plans.values()),unmapped=unmapped,ambiguous=ambiguous,scanned_segments=nsegments,validated_native_width_ndrs=ndrs)
(out/'antenna-net-map.json').write_text(json.dumps(r,indent=2));print(json.dumps(dict(markers=len(rows),unique_nets=len(plans),unmapped=unmapped,ambiguous=ambiguous,existing_diodes=sum(bool(p['existing_diodes']) for p in plans.values())),indent=2))
assert not ambiguous and not unmapped
