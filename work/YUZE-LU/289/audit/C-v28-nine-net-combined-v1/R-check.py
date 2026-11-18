import pya,re,json,hashlib
from pathlib import Path
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');p=root/'audit/C-v28-nine-net-combined-v1';meta=p;src=root/'cu/runs/C-v28-actual-i8-h50/flow/results/nangate45/c-overlay-current/base'
cases=[{'name': 'R167', 'net': 'services.engine[2].genblk1.recurrent.leaf.cmd_data[167]', 'pin': [198000, 1062000, 202000, 1066000], 'origin': [144000, 144000], 'leaf': '/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt252/delivery/native/6_final.def', 'leafnet': 'rsp_data[167]', 'roi': [880000, 5210000, 1080000, 5420000], 'inner': [965000, 5290000, 992000, 5340000]}, {'name': 'R202', 'net': 'services.engine[2].genblk1.recurrent.leaf.cmd_data[202]', 'pin': [198000, 1142000, 202000, 1146000], 'origin': [144000, 144000], 'leaf': '/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt252/delivery/native/6_final.def', 'leafnet': 'rsp_data[202]', 'roi': [880000, 5630000, 1080000, 5840000], 'inner': [965000, 5710000, 992000, 5760000]}, {'name': 'R20', 'net': 'services.engine[2].genblk1.recurrent.leaf.cmd_data[20]', 'pin': [198000, 1158000, 202000, 1162000], 'origin': [144000, 144000], 'leaf': '/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt252/delivery/native/6_final.def', 'leafnet': 'rsp_data[20]', 'roi': [880000, 5690000, 1080000, 5920000], 'inner': [965000, 5770000, 992000, 5840000]}]
cases.append(dict(name='Rrd50',net='i289_actual_v28_i8_h50_iso24_source',pin=[198000,774000,202000,778000],origin=[144000,144000],leaf='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-166-r-local-state/attempt252/delivery/native/6_final.def',leafnet='rd_data[50]',roi=[880000,3790000,1080000,4000000],inner=[940000,3850000,1030000,3930000]))
a=pya.Layout();a.read(str(src/'6_final.gds'));b=pya.Layout();b.read(str(p/'patched.gds'));assert a.dbu==b.dbu==.0001
union_roi=pya.Region()
for c in cases:union_roi.insert(pya.Box(*c['roi']))
def local_layer(lay,idx):
 # Conservative bbox query includes every shape intersecting either ROI; exact integer clipping is unchanged.
 # Search expands one database unit to avoid floating-boundary exclusion in the DBox overload.
 out=pya.Region()
 for c in cases:
  v=c['roi'];query=pya.DBox((v[0]-1)*lay.dbu,(v[1]-1)*lay.dbu,(v[2]+1)*lay.dbu,(v[3]+1)*lay.dbu)
  out+=pya.Region(lay.top_cell().begin_shapes_rec_touching(idx,query))&pya.Region(pya.Box(*v))
 return out
a10=local_layer(a,a.layer(29,0));b10=local_layer(b,b.layer(29,0))
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
obs=pya.Region()
for line in (p/'m10-obstructions.tsv').read_text().splitlines():obs.insert(pya.Box(*[int(v)*5 for v in line.split('\t')]))
expected_old=pya.Region();expected_new=pya.Region()
results=[]
for c in cases:
 roi=pya.Region(pya.Box(*c['roi']));aa=a10&roi;bb=b10&roi;inner=pya.Region(pya.Box(*c['inner']))
 leaftext=body(Path(c['leaf']),c['leafnet']);assert '( PIN '+c['leafnet']+' )' in leaftext
 pin=pya.Region(pya.Box(*[v*5 for v in c['pin']]))
 leaf=route_region(leaftext,c['origin'])
 old_parent=route_region(body(p/'before.def',c['net']),[0,0])&roi
 new_parent=route_region(body(p/'patched.def',c['net']),[0,0])&roi
 assert ((new_parent-old_parent)&obs).is_empty(), 'New parent conductor overlaps installed macro OBS'
 old=(old_parent+leaf+pin)&roi;old.merge()
 new=(route_region(body(p/'patched.def',c['net']),[0,0])+leaf+pin)&roi;new.merge()
 assert (old-aa).is_empty() and (new-bb).is_empty();components(aa,old);components(bb,new)
 expected_old+=old;expected_new+=new
 add=new-old;remove=old-new;assert (add&obs).is_empty(), 'Added parent M10 intersects installed macro OBS';assert (add-(bb-aa)).is_empty();assert (remove-(aa-bb)).is_empty()
 assert new.count()==1 and (add&(aa-old)).is_empty();assert new.separation_check(aa-old,8000).is_empty(),'foreign spacing'
 def markers(q):return {n:[str(x) for x in es.each() if not (pya.Region(x.bbox())&inner).is_empty()] for n,es in [('space',q.space_check(8000)),('notch',q.notch_check(8000)),('width',q.width_check(8000))]}
 pre=markers(aa);post=markers(bb);assert all(not x for x in post.values()),post
 results.append(dict(name=c['name'],net=c['net'],added_area_um2=add.area()*1e-8,removed_area_um2=remove.area()*1e-8,actual_component_exact=True,component_count=1,foreign_overlap=False,foreign_spacing800nm_passed=True,before=pre,after=post))
 print('COMPONENT_PASS',c['name'],flush=True)
assert ((expected_new-expected_old)^(b10-a10)).is_empty(), 'Unexplained actual M10 addition across all ROIs'
assert ((expected_old-expected_new)^(a10-b10)).is_empty(), 'Unexplained actual M10 removal across all ROIs'
for l in a.layer_infos():
 if (l.layer,l.datatype)==(29,0):continue
 x=local_layer(a,a.layer(l));y=local_layer(b,b.layer(l));assert (x^y).is_empty(),str(l);print('LAYER_EQUAL',str(l),flush=True)
files=[src/'6_final.gds',p/'patched.gds',p/'patched.odb',p/'before.def',p/'patched.def',meta/'pins-v2.tsv',meta/'vias.tsv',Path(__file__)]+[Path(c['leaf']) for c in cases]
result=dict(passed=True,scope='Four local parent-only M10 reroutes, preserving macro pins and the source leaf material; actual connected-component equality including actual leaf routes, foreign spacing/overlap, original 800nm width/space/notch and unchanged other local layers. Not complete backend signoff.',cases=results,other_layers_equal=True,hashes={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files})
(p/'R-material-receipt.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
