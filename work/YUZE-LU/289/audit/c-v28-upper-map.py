from pathlib import Path
import re,json,hashlib
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117')
p=r/'audit/C-v28-upper-map';p.mkdir(exist_ok=True)
meta=r/'audit/C-v28-i8h50-physical/rcx-material-120132'
src=r/'cu/runs/C-v28-actual-i8-h50/flow/results/nangate45/c-overlay-current/base/6_final.def'
assert src.read_bytes()==(meta/'before.def').read_bytes()
rois=[('E9','metal9',[1887,489,1891,493]),('G9','metal9',[1391,675,1395,679]),('dot9','metal9',[2024,830,2028,834]),('Gvia','via9',[1373,910,1376,913])]
rois=[(n,l,[round(x*2000) for x in b]) for n,l,b in rois]
widths={n:int(w) for n,w in [x.split() for x in (meta/'layers.tsv').read_text().splitlines()]}
vias={}
for x in (meta/'vias.tsv').read_text().splitlines():
 n,l,*v=x.split();vias.setdefault(n,[]).append((l,list(map(int,v))))
def intersects(a,b):return a[0]<=b[2] and b[0]<=a[2] and a[1]<=b[3] and b[1]<=a[3]
text=src.read_text();nt=text.split('\nNETS ',1)[1].split('\nEND NETS',1)[0];hits=[]
for body in re.split(r'(?m)^\s*-(?= )',nt)[1:]:
 name=body.split()[0]
 for m in re.finditer(r'(?:\+ ROUTED|\bNEW)\s+(\S+)\s+(.*?)(?=\bNEW|;|$)',body,re.S):
  layer,seq=m.groups();prev=None;pe=None
  for t in re.finditer(r'\(\s*(\*|-?\d+)\s+(\*|-?\d+)(?:\s+(-?\d+))?\s*\)|(\S+)',seq):
   x,y,ext,n=t.groups();shapes=[]
   if x is not None:
    pt=(prev[0] if x=='*' else int(x),prev[1] if y=='*' else int(y));half=widths[layer]//2;ce=half if ext is None else int(ext)
    if prev and layer in ('metal9','via9'):
     if pt[0]==prev[0]:lo,hi=sorted([(prev[1],pe),(pt[1],ce)]);v=[pt[0]-half,lo[0]-lo[1],pt[0]+half,hi[0]+hi[1]]
     else:
      assert pt[1]==prev[1];lo,hi=sorted([(prev[0],pe),(pt[0],ce)]);v=[lo[0]-lo[1],pt[1]-half,hi[0]+hi[1],pt[1]+half]
     shapes.append((layer,v,'wire'))
    prev=pt;pe=ce
   elif n in vias:
    shapes += [(l,[v+prev[i%2] for i,v in enumerate(box)],n) for l,box in vias[n] if l in ('metal9','via9')]
   for l,v,kind in shapes:
    for roi,rl,b in rois:
     if l==rl and intersects(v,b):hits.append(dict(roi=roi,net=name,layer=l,box_dbu=v,kind=kind,branch=m.group(0).strip()))
result=dict(source=str(src),source_sha256=hashlib.sha256(src.read_bytes()).hexdigest(),rois=rois,hits=hits)
(p/'top-route-hits.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
