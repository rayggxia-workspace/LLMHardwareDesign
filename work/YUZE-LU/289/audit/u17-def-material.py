import pya,re,json,hashlib
from pathlib import Path
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');base=r/'u-physical/rcx-def-uncached-119788/normal';meta=r/'audit/U-antenna/guard-v1-map'
width={n:int(w) for n,w in (s.split('\t') for s in (meta/'layers.tsv').read_text().splitlines())};vias={};vlayers={}
for s in (meta/'vias.tsv').read_text().splitlines():
 n,l,*b=s.split('\t');vias.setdefault(n,[]).append((l,list(map(int,b))))
 if l.startswith('metal'):vlayers.setdefault(n,set()).add(l)
targets={'i289_repeater_store124_net','net22175','net38689',r'e_out_data\[26\]','net38652','net38650'}
allregions={};canonical={}
for label in ('before','after'):
 text=(base/(label+'.def')).read_text().split('\nNETS ',1)[1].split('\nEND NETS',1)[0];nets={}
 for e in re.finditer(r'^\s*-\s+(\S+)\s+(.*?);\s*$',text,re.M|re.S):
  net,body=e.groups()
  if net not in targets:continue
  regions={};routes=[]
  def add(layer,box):regions.setdefault(layer,pya.Region()).insert(pya.Box(*box))
  for m in re.finditer(r'(?:\+ ROUTED|\bNEW)\s+(\S+)\s+(.*?)(?=\bNEW|$)',body,re.S):
   layer,seq=m.groups();prev=None;pe=None
   for t in re.finditer(r'\(\s*(\*|-?\d+)\s+(\*|-?\d+)(?:\s+(-?\d+))?\s*\)|(\S+)',seq):
    x,y,ext,n=t.groups()
    if x is not None:
     pt=(prev[0] if x=='*' else int(x),prev[1] if y=='*' else int(y));ce=None if ext is None else int(ext);h=width[layer]//2
     if prev and prev!=pt:
      a=h if pe is None else pe;b=h if ce is None else ce
      if pt[0]==prev[0]:
       lo,hi=sorted([(prev[1],a),(pt[1],b)]);box=[pt[0]-h,lo[0]-lo[1],pt[0]+h,hi[0]+hi[1]]
      else:
       assert pt[1]==prev[1];lo,hi=sorted([(prev[0],a),(pt[0],b)]);box=[lo[0]-lo[1],pt[1]-h,hi[0]+hi[1],pt[1]+h]
      add(layer,box)
      fmt=lambda p,e:'( '+str(p[0])+' '+str(p[1])+(' '+str(e) if e is not None else '')+' )'
      routes.append('NEW '+layer+' '+fmt(prev,pe)+' '+fmt(pt,ce))
     prev=pt;pe=ce
    elif n in vias:
     assert prev
     for l,box in vias[n]:add(l,[v+prev[i%2] for i,v in enumerate(box)])
     routes.append('NEW '+layer+' ( '+str(prev[0])+' '+str(prev[1])+' ) '+n)
     ls=vlayers[n];assert layer in ls and len(ls)==2;layer=next(l for l in ls if l!=layer);pe=None
    else:assert n in ('TAPER','+','USE','SIGNAL'),n
  nets[net]=regions;canonical[label,net]=routes
 assert set(nets)==targets;allregions[label]=nets
rows=[]
for net in sorted(targets):
 a=allregions['before'][net];b=allregions['after'][net]
 for layer in sorted(a.keys()|b.keys()):
  diff=a.get(layer,pya.Region())^b.get(layer,pya.Region())
  rows.append(dict(net=net,layer=layer,equal=diff.is_empty(),xor_area_um2=diff.area()/4000000,boxes_dbu=[str(p.bbox()) for p in diff.each()]))
out=r/'audit/U-v17-six-net-def-material.json';result=dict(passed=all(x['equal'] for x in rows),scope='Six target nets: DEF per-layer wire rectangles with explicit point extensions and native half-width defaults plus exact actual via enclosures/cuts; layer toggles at every via; polygon-union XOR',source_sha256={str(base/(x+'.def')):hashlib.sha256((base/(x+'.def')).read_bytes()).hexdigest() for x in ('before','after')},layers=rows)
out.write_text(json.dumps(result,indent=2));(r/'audit/U-v17-six-net-canonical-routes.json').write_text(json.dumps({net:canonical['after',net] for net in sorted(targets)},indent=2));print(json.dumps(dict(passed=result['passed'],differences=[x for x in rows if not x['equal']]),indent=2))
