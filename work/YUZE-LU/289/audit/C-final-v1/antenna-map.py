"""Read-only exact antenna report-to-C-route mapping. No diode edits or guessed net ownership."""
import pya,json,re,collections,hashlib,os,xml.etree.ElementTree as E
from pathlib import Path
out=Path.cwd();res=Path(os.environ['C_ANT_RES']);report=Path(os.environ['C_ANT_REPORT']);binding=Path(os.environ['C_ANT_BINDING']);config=Path(os.environ['C_ANT_RUN'])/'config.mk'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
bound=json.loads(binding.read_text());assert bound['completed'] and bound['gds_sha256']==sha(res/'6_final.gds') and bound['report_sha256']==sha(report)
assert Path(bound['gds_path']).resolve()==(res/'6_final.gds').resolve() and Path(bound['report_path']).resolve()==report.resolve()
assert sha(bound['deck_path'])==bound['deck_sha256']
top=re.findall(r'^export DESIGN_NAME\s*=\s*(\S+)',config.read_text(),re.M)[-1];assert top=='cfj_group_c_memory_legacy' and (out/'design-name.txt').read_text().strip()==top
units=int((out/'dbu.txt').read_text());dbu=.0001;scale=1/units/dbu;assert abs(scale-round(scale))<1e-9;scale=int(round(scale))
rows=[];regions=[];nonparent=[]
for original_id,item in enumerate(E.parse(str(report)).findall('.//items/item')):
 cat=item.findtext('category').strip("'\"");assert 'ANTENNA' in cat,('Non-antenna item supplied',cat)
 cell=item.findtext('cell');values=[v.text for v in item.findall('values/value')]
 if cell!=top:nonparent.append(dict(report_id=original_id,category=cat,cell=cell,values=values));continue
 match=re.fullmatch(r'METAL(10|[1-9])_ANTENNA',cat);assert match,cat
 shapes=[v[9:] for v in values if v.startswith('polygon: ')];assert shapes
 reg=pya.Region()
 for geom in shapes:reg.insert(pya.DPolygon.from_s(geom).to_itype(dbu))
 b=reg.bbox();rows.append(dict(report_id=original_id,category=cat,layer='metal'+match[1],geometry=shapes,bbox_dbu=[b.left,b.bottom,b.right,b.top],hits=[]));regions.append(reg)
grid=collections.defaultdict(set);pitch=100000
for i,row in enumerate(rows):
 a,b,c,d=row['bbox_dbu']
 for x in range(a//pitch,c//pitch+1):
  for y in range(b//pitch,d//pitch+1):grid[row['layer'],x,y].add(i)
def add(net,layer,box,kind):
 if not layer.startswith('metal'):return
 box=[v*scale for v in box];a,b,c,d=box;ids=set()
 for x in range(a//pitch,c//pitch+1):
  for y in range(b//pitch,d//pitch+1):ids.update(grid.get((layer,x,y),()))
 for i in ids:
  hit=regions[i]&pya.Region(pya.Box(*box))
  if not hit.is_empty():rows[i]['hits'].append(dict(net=net,kind=kind,area_um2=hit.area()*dbu**2,box_dbu=box))
width={n:int(w) for n,w in (s.split('\t') for s in (out/'layers.tsv').read_text().splitlines())};vias=collections.defaultdict(list);vmetal=collections.defaultdict(set)
for s in (out/'vias.tsv').read_text().splitlines():
 n,l,*b=s.split('\t');vias[n].append((l,list(map(int,b))))
 if l.startswith('metal'):vmetal[n].add(l)
for s in (out/'bpins.tsv').read_text().splitlines():
 port,net,layer,*b=s.split('\t');add(net,layer,list(map(int,b)),'BPin:'+port)
endpoints=collections.defaultdict(list);norm=lambda x:x.replace('\\','')
for s in (out/'endpoints.tsv').read_text().splitlines():
 net,inst,master,pin,direction,x,y,orient,w,h=s.split('\t');endpoints[norm(net)].append(dict(instance=inst,master=master,pin=pin,direction=direction,x=int(x),y=int(y),orient=orient,width=int(w),height=int(h)))
text=(res/'6_final.def').read_text();assert int(re.search(r'UNITS DISTANCE MICRONS\s+(\d+)',text)[1])==units
section=text.split('\nNETS ',1)[1].split('\nEND NETS',1)[0];nsegments=0;checked_nets=0
for entry in re.finditer(r'^\s*-\s+(\S+)\s+(.*?);\s*$',section,re.M|re.S):
 net,body=entry.groups();assert not re.search(r'\+\s*(FIXED|COVER|NONDEFAULTRULE)\b',body),('Unreviewed route encoding',net)
 prefix=re.split(r'\+ ROUTED|\bNEW',body,maxsplit=1)[0]
 if re.search(r'\+\s+USE\s+(POWER|GROUND)\b',prefix):continue
 declared={(norm(a),norm(b)) for a,b in re.findall(r'\(\s*(\S+)\s+(\S+)\s*\)',prefix) if a!='PIN'}
 actual={(norm(e['instance']),norm(e['pin'])) for e in endpoints[norm(net)]};assert declared==actual,('ODB/DEF endpoint mismatch',net,sorted(declared^actual)[:8]);checked_nets+=1
 for m in re.finditer(r'(?:\+ ROUTED|\bNEW)\s+(\S+)\s+(.*?)(?=\bNEW|$)',body,re.S):
  layer,seq=m.groups();assert layer in width;previous=None;pe=None
  for tok in re.finditer(r'\(\s*(\*|-?\d+)\s+(\*|-?\d+)(?:\s+(-?\d+))?\s*\)|(\S+)',seq):
   x,y,ext,name=tok.groups()
   if x is not None:
    point=(previous[0] if x=='*' else int(x),previous[1] if y=='*' else int(y));half=width[layer]//2;ce=half if ext is None else int(ext)
    if previous:
     if point[0]==previous[0]:lo,hi=sorted([(previous[1],pe),(point[1],ce)]);box=[point[0]-half,lo[0]-lo[1],point[0]+half,hi[0]+hi[1]]
     else:
      assert point[1]==previous[1];lo,hi=sorted([(previous[0],pe),(point[0],ce)]);box=[lo[0]-lo[1],point[1]-half,hi[0]+hi[1],point[1]+half]
     add(net,layer,box,'wire');nsegments+=1
    previous=point;pe=ce
   elif name in vias:
    assert previous
    for vl,box in vias[name]:add(net,vl,[v+previous[i%2] for i,v in enumerate(box)],'via:'+name)
    ls=vmetal[name];assert len(ls)==2 and layer in ls,(net,name,layer);layer=next(v for v in ls if v!=layer);pe=width[layer]//2
   else:raise AssertionError(('Unknown route token',net,name))
network={};ambiguous=[];unmapped=[]
for row in rows:
 nets=sorted({h['net'] for h in row['hits']});row['nets']=nets
 if not nets:unmapped.append(row['report_id']);continue
 if len(nets)!=1:ambiguous.append(dict(report_id=row['report_id'],nets=nets));continue
 net=nets[0]
 if net not in network:
  ep=endpoints[norm(net)];network[net]=dict(net=net,report_ids=[],existing_parent_diodes=[x for x in ep if x['master']=='ANTENNA_X1'],standard_endpoints=[x for x in ep if re.search(r'_X\d+$',x['master']) and x['master']!='ANTENNA_X1'])
 network[net]['report_ids'].append(row['report_id'])
r=dict(mapping_complete=not(nonparent or ambiguous or unmapped),accepted=False,scope='Read-only polygon intersection with actual route metal/via enclosures and verified ODB endpoint connectivity. No diode insertion recommendation or count inferred. Nonparent/ambiguous/unmapped items require further investigation.',markers=rows,nonparent_markers=nonparent,ambiguous=ambiguous,unmapped=unmapped,networks=list(network.values()),checked_endpoint_nets=checked_nets,scanned_segments=nsegments,dbu_um=dbu,source_sha256={str(p):sha(p) for p in (res/'6_final.def',res/'6_final.odb',res/'6_final.gds',report,binding,out/'design-name.txt',out/'layers.tsv',out/'vias.tsv',out/'bpins.tsv',out/'endpoints.tsv',Path(__file__))})
(out/'antenna-net-map.json').write_text(json.dumps(r,indent=2));print(json.dumps(dict(mapping_complete=r['mapping_complete'],parent_markers=len(rows),nonparent=len(nonparent),ambiguous=len(ambiguous),unmapped=len(unmapped),mapped_nets=len(network)),indent=2))
