import pya,re,json,hashlib
from pathlib import Path
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');p=root/'audit/C-v27-m10/patch-v1';meta=p.parent;src=root/'cu/runs/C-v27-joint-e20-h30/flow/results/nangate45/c-overlay-current/base'
cases=[dict(name='S71',net='dma_s_rsp_data[71]',pin=[2310190,510140,2314190,514140],origin=[2288000,144000],leaf='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-200-compact-local-s/run08-base0/results/0/flow/results/nangate45/local_s_base/base/6_final.def',leafnet='rsp_data[71]',roi=[11500000,2500000,11600000,2600000],inner=[11545000,2557000,11554000,2564000],added_area=.006),dict(name='R114',net='services.engine[2].a[114]',pin=[366000,2094000,370000,2098000],origin=[144000,144000],leaf='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt252/delivery/native/6_final.def',leafnet='load_data[114]',roi=[1800000,10420000,1900000,10520000],inner=[1841000,10458000,1852000,10474000],added_area=.33015)]
a=pya.Layout();a.read(str(src/'6_final.gds'));b=pya.Layout();b.read(str(p/'patched.gds'));assert a.dbu==b.dbu==.0001
union_roi=pya.Region()
for c in cases:union_roi.insert(pya.Box(*c['roi']))
a10=pya.Region(a.top_cell().begin_shapes_rec(a.layer(29,0)))&union_roi;b10=pya.Region(b.top_cell().begin_shapes_rec(b.layer(29,0)))&union_roi
vias={}
for x in (meta/'vias.tsv').read_text().splitlines():
 n,l,*v=x.split('\t');vias.setdefault(n,[]).append((l,list(map(int,v))))
def body(path,name):
 t=path.read_text().split('\nNETS ',1)[1].split('\nEND NETS',1)[0]
 return next(z for z in re.split(r'(?m)^\s*-(?= )',t)[1:] if z.split()[0].replace('\\','')==name)
def route_region(text,origin):
 out=pya.Region()
 def add(v):out.insert(pya.Box(*[(x+origin[i%2])*5 for i,x in enumerate(v)]))
 for m in re.finditer(r'(?:\+ ROUTED|\bNEW)\s+(\S+)\s+(.*?)(?=\bNEW|;|$)',text,re.S):
  layer,seq=m.groups();prev=None;pe=None
  for t in re.finditer(r'\(\s*(\*|-?\d+)\s+(\*|-?\d+)(?:\s+(-?\d+))?\s*\)|(\S+)',seq):
   x,y,ext,n=t.groups()
   if x is not None:
    pt=(prev[0] if x=='*' else int(x),prev[1] if y=='*' else int(y));ce=800 if ext is None else int(ext)
    if prev and layer=='metal10':
     if pt[0]==prev[0]:lo,hi=sorted([(prev[1],pe),(pt[1],ce)]);v=[pt[0]-800,lo[0]-lo[1],pt[0]+800,hi[0]+hi[1]]
     else:assert pt[1]==prev[1];lo,hi=sorted([(prev[0],pe),(pt[0],ce)]);v=[lo[0]-lo[1],pt[1]-800,hi[0]+hi[1],pt[1]+800]
     add(v)
    prev=pt;pe=ce
   elif n in vias:
    for l,v in vias[n]:
     if l=='metal10':add([k+prev[i%2] for i,k in enumerate(v)])
   else:assert n in ('TAPER','+','USE','SIGNAL') or (n.startswith('via') and layer not in ('metal9','metal10')),n
 return out
def components(actual,target):
 comp=pya.Region()
 for poly in actual.merged().each():
  q=pya.Region(poly)
  if not (q&target).is_empty():comp+=q
 assert (comp^target).is_empty(),'unaccounted connected actual M10 geometry'
results=[]
for c in cases:
 roi=pya.Region(pya.Box(*c['roi']));aa=a10&roi;bb=b10&roi;inner=pya.Region(pya.Box(*c['inner']))
 leaftext=body(Path(c['leaf']),c['leafnet']);assert '( PIN '+c['leafnet']+' )' in leaftext
 pin=pya.Region(pya.Box(*[v*5 for v in c['pin']]))
 leaf=route_region(leaftext,c['origin'])
 old=(route_region(body(p/'before.def',c['net']),[0,0])+leaf+pin)&roi;old.merge()
 new=(route_region(body(p/'patched.def',c['net']),[0,0])+leaf+pin)&roi;new.merge()
 assert (old-aa).is_empty() and (new-bb).is_empty();components(aa,old);components(bb,new)
 add=bb-aa;remove=aa-bb;assert remove.is_empty();assert ((new-old)^add).is_empty();assert abs(add.area()*1e-8-c['added_area'])<1e-10
 assert new.count()==1 and (add&(aa-old)).is_empty();assert new.separation_check(aa-old,8000).is_empty(),'foreign spacing'
 def markers(q):return {n:[str(x) for x in es.each() if not (pya.Region(x.bbox())&inner).is_empty()] for n,es in [('space',q.space_check(8000)),('notch',q.notch_check(8000)),('width',q.width_check(8000))]}
 pre=markers(aa);post=markers(bb);assert all(not x for x in post.values()),post
 results.append(dict(name=c['name'],net=c['net'],added_area_um2=add.area()*1e-8,removed_area_um2=0,actual_component_exact=True,component_count=1,foreign_overlap=False,foreign_spacing800nm_passed=True,before=pre,after=post))
 print('COMPONENT_PASS',c['name'],flush=True)
for l in a.layer_infos():
 if (l.layer,l.datatype)==(29,0):continue
 x=pya.Region(a.top_cell().begin_shapes_rec(a.layer(l)))&union_roi;y=pya.Region(b.top_cell().begin_shapes_rec(b.layer(l)))&union_roi;assert (x^y).is_empty(),str(l)
files=[src/'6_final.gds',p/'patched.gds',p/'patched.odb',p/'before.def',p/'patched.def',meta/'nearby-pins.tsv',meta/'vias.tsv',Path(__file__)]+[Path(c['leaf']) for c in cases]
result=dict(passed=True,scope='Two local same-net M10 bridges; actual connected-component equality including actual leaf routes, foreign spacing/overlap, original 800nm width/space/notch and unchanged other local layers. Not complete backend signoff.',cases=results,other_layers_equal=True,hashes={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files})
(p/'gds-local-receipt.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
