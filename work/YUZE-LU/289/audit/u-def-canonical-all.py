"""All-net explicit DEF geometry audit and conservative route segmentation."""
import pya,re,json,hashlib,os,time,shutil
from pathlib import Path
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');base=Path(os.environ.get('U_CANON_BASE',str(r/'u-physical/rcx-def-uncached-119788/normal')));meta=r/'audit/U-antenna/guard-v1-map';out=Path(os.environ['U_CANON_OUT']);out.mkdir(exist_ok=False)
shutil.copyfile(__file__,out/'checker.py')
width={n:int(w) for n,w in (s.split('\t') for s in (meta/'layers.tsv').read_text().splitlines())};vias={};vlayers={}
for s in (meta/'vias.tsv').read_text().splitlines():
 n,l,*b=s.split('\t');vias.setdefault(n,[]).append((l,list(map(int,b))))
 if l.startswith('metal'):vlayers.setdefault(n,set()).add(l)
pat=re.compile(r'^\s*-\s+(\S+)\s+(.*?);\s*$',re.M|re.S);texts={x:(base/(x+'.def')).read_text() for x in ('before','after')}
def sec(text,n):
 m=re.search(r'\n'+n+r'\s+\d+\s*;(.*?)\nEND '+n,text,re.S);assert m,n;return m[1]
for name in ('PINS','SPECIALNETS','COMPONENTS'):assert sec(texts['before'],name)==sec(texts['after'],name),name
netsections={x:sec(v,'NETS') for x,v in texts.items()};netbodies={x:{m[1]:m[2] for m in pat.finditer(v)} for x,v in netsections.items()};assert netbodies['before'].keys()==netbodies['after'].keys()
fmt=lambda p,e:'( '+str(p[0])+' '+str(p[1])+(' '+str(e) if e is not None else '')+' )'
def parse(body):
 regions={};routes=[];found=False;prefix=None
 def add(l,b):regions.setdefault(l,pya.Region()).insert(pya.Box(*b))
 for m in re.finditer(r'(?:\+ ROUTED|\bNEW)\s+(\S+)\s+(.*?)(?=\bNEW|$)',body,re.S):
  if not found:prefix=body[:m.start()].strip();found=True
  layer,seq=m.groups();assert layer in width,layer;prev=None;pe=None;sawvia=False
  for t in re.finditer(r'\(\s*(\*|-?\d+)\s+(\*|-?\d+)(?:\s+(-?\d+))?\s*\)|(\S+)',seq):
   x,y,ext,n=t.groups()
   if x is not None:
    pt=(prev[0] if x=='*' else int(x),prev[1] if y=='*' else int(y));ce=None if ext is None else int(ext);h=width[layer]//2
    if prev:
     a=h if pe is None else pe;b=h if ce is None else ce
     if pt[0]==prev[0]:
      lo,hi=sorted([(prev[1],a),(pt[1],b)]);box=[pt[0]-h,lo[0]-lo[1],pt[0]+h,hi[0]+hi[1]]
     else:
      assert pt[1]==prev[1],(prev,pt);lo,hi=sorted([(prev[0],a),(pt[0],b)]);box=[lo[0]-lo[1],pt[1]-h,hi[0]+hi[1],pt[1]+h]
     add(layer,box);routes.append(layer+' '+fmt(prev,pe)+' '+fmt(pt,ce))
    prev=pt;pe=ce
   elif n in vias:
    assert prev
    for l,box in vias[n]:add(l,[v+prev[i%2] for i,v in enumerate(box)])
    routes.append(layer+' '+fmt(prev,None)+' '+n);sawvia=True
    ls=vlayers[n];assert layer in ls and len(ls)==2,(layer,n);layer=next(l for l in ls if l!=layer);pe=None
   else:assert n=='TAPER',('Unknown route token',n)
  assert prev is not None
 if not found:return regions,body
 assert routes,(prefix,'empty routes')
 return regions,prefix+'\n      + ROUTED '+routes[0]+''.join('\n      NEW '+v for v in routes[1:])
rows=[];canonical={};bad=[];start=time.time()
for i,net in enumerate(netbodies['before']):
 try:a,_=parse(netbodies['before'][net]);b,canonical[net]=parse(netbodies['after'][net])
 except Exception as e:raise RuntimeError((net,str(e))) from e
 for layer in sorted(a.keys()|b.keys()):
  diff=a.get(layer,pya.Region())^b.get(layer,pya.Region())
  if not diff.is_empty():bad.append(dict(net=net,layer=layer,xor_area_um2=diff.area()/4000000,boxes_dbu=[str(p.bbox()) for p in diff.each()]))
 if i%10000==0:print(json.dumps(dict(nets_checked=i,elapsed=time.time()-start,differences=len(bad))),flush=True)
# Reparse each canonical route to prove own serialization preserves per-layer union.
for net in netbodies['after']:
 a,_=parse(netbodies['after'][net]);b,_=parse(canonical[net])
 assert a.keys()==b.keys() and all((a[l]^b[l]).is_empty() for l in a),('Canonical readback differs',net)
newsection=pat.sub(lambda m:'\n    - '+m[1]+' '+canonical[m[1]]+' ;',netsections['after'])
text=texts['after'].replace(netsections['after'],newsection,1);p=out/'canonical.def';p.write_text(text)
assert all(sec(text,n)==sec(texts['after'],n) for n in ('PINS','SPECIALNETS','COMPONENTS'))
files=[base/'before.def',base/'after.def',meta/'layers.tsv',meta/'vias.tsv',out/'checker.py',p]
v=dict(passed=not bad,nets_checked=len(canonical),geometry_differences=bad,canonical_readback_material_exact=True,components_bpins_specialnets_byte_exact=True,scope='All signal-net per-layer rectangle/via polygon union, explicit DEF extensions and actual via layer transitions; fail on unknown tokens. Canonical stream splits each segment and each via, preserves net headers and all non-NETS text.',source_sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files})
(out/'receipt.json').write_text(json.dumps(v,indent=2));print(json.dumps(dict(passed=v['passed'],nets_checked=v['nets_checked'],differences=len(bad)),indent=2))
