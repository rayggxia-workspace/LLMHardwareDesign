import pya,re,json,hashlib
from pathlib import Path
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117')
out=root/'audit/U-v15-pg-diagnostic';res=out/'flow/results/nangate45/u-overlay-current/base'
meta=root/'audit/U-antenna/guard-v1-map'
width={n:int(w) for n,w in (x.split('\t') for x in (meta/'layers.tsv').read_text().splitlines())}
vias={}
for x in (meta/'vias.tsv').read_text().splitlines():
 n,l,*b=x.split('\t');vias.setdefault(n,[]).append((l,list(map(int,b))))
text=(res/'6_final.def').read_text();body=next(m[2] for m in re.finditer(r'^\s*-\s+(\S+)\s+(.*?);\s*$',text.split('\nNETS ',1)[1].split('\nEND NETS',1)[0],re.M|re.S) if m[1].replace('\\','')=='datapath.legacy_rsp_data[90]')
r=pya.Region();boxes=[]
def add(layer,b):
 if layer=='metal1':r.insert(pya.Box(*[v*5 for v in b]));boxes.append([v/2000 for v in b])
for m in re.finditer(r'(?:\+ ROUTED|\bNEW)\s+(\S+)\s+(.*?)(?=\bNEW|$)',body,re.S):
 layer,seq=m.groups();prev=None;pe=None
 for t in re.finditer(r'\(\s*([*+-]?\d*|\*)\s+([*+-]?\d*|\*)(?:\s+(-?\d+))?\s*\)|(\S+)',seq):
  x,y,ext,n=t.groups()
  if x is not None:
   pt=(prev[0] if x=='*' else int(x),prev[1] if y=='*' else int(y));h=width[layer]//2;ce=h if ext is None else int(ext)
   if prev:
    if pt[0]==prev[0]:
     lo,hi=sorted([(prev[1],pe),(pt[1],ce)]);b=[pt[0]-h,lo[0]-lo[1],pt[0]+h,hi[0]+hi[1]]
    else:
     assert pt[1]==prev[1];lo,hi=sorted([(prev[0],pe),(pt[0],ce)]);b=[lo[0]-lo[1],pt[1]-h,hi[0]+hi[1],pt[1]+h]
    add(layer,b)
   prev=pt;pe=ce
  elif n in vias:
   for l,b in vias[n]:add(l,[v+prev[i%2] for i,v in enumerate(b)])
  else:assert n in ('TAPER','+','USE','SIGNAL'),n
lay=pya.Layout();lay.read(str(res/'6_final.gds'));assert lay.dbu==.0001
allm=pya.Region(lay.top_cell().begin_shapes_rec(lay.layer(11,0)))
roi=pya.Region(pya.DBox(30,44.4,130,45).to_itype(lay.dbu));rail=pya.Region(pya.DBox(30,44.715,130,44.79).to_itype(lay.dbu))
net=r&roi;missing=net-allm;overlap=net&rail
result=dict(scope='Actual DEF net90 M1 wires and via enclosures versus merged GDS M1 and PSM-reported y44.715-44.790 band',net='datapath.legacy_rsp_data[90]',def_sha256=hashlib.sha256((res/'6_final.def').read_bytes()).hexdigest(),gds_sha256=hashlib.sha256((res/'6_final.gds').read_bytes()).hexdigest(),m1_boxes_in_roi=[b for b in boxes if b[0]<130 and b[2]>30 and b[1]<45 and b[3]>44.4],net_m1_missing_from_gds_area=missing.area()*1e-8,net_m1_intersection_reported_rail_band_area=overlap.area()*1e-8,actual_m1_in_rail_band_area=(allm&rail).area()*1e-8)
(out/'net90-m1-physical.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
assert missing.is_empty() and overlap.is_empty()
