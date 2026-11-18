import pya,json,re,hashlib
from pathlib import Path
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit');p=r/'C-m10-notch14-v2';src=r/'C-m10-notch-v1/patched.gds'
a=pya.Layout();a.read(str(src));b=pya.Layout();b.read(str(p/'patched.gds'));assert a.dbu==b.dbu==.0001
box=pya.Box(13600000,5750000,13720000,5960000);roi=pya.Region(box)
a10=pya.Region(a.top_cell().begin_shapes_rec(a.layer(29,0)))&roi;b10=pya.Region(b.top_cell().begin_shapes_rec(b.layer(29,0)))&roi
added=b10-a10;removed=a10-b10;assert removed.is_empty() and not added.is_empty()
# Independent DEF-to-rectangle reconstruction of the exact same net, plus its actual LEF pin.
def netregion(path):
 s=path.read_text().split('\nNETS ',1)[1].split('\nEND NETS',1)[0]
 body=next(x for x in re.split(r'(?m)^\s*-(?= )',s)[1:] if x.split()[0].replace('\\','')=='dma_s_rsp_data[14]')
 out=pya.Region(pya.Box(2734190*5,1158140*5,2738190*5,1162140*5))
 # Actual S leaf rsp_data14 has an internal M10 extension above its abstract pin.
 # Bind it to the delivered leaf DEF by the exact port/net and route, then translate R0 origin (1144,72)um.
 leaf=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-200-compact-local-s/run08-base0/results/0/flow/results/nangate45/local_s_base/base/6_final.def')
 ls=leaf.read_text().split('\nNETS ',1)[1].split('\nEND NETS',1)[0]
 ln=next(z for z in re.split(r'(?m)^\s*-(?= )',ls)[1:] if z.split()[0]=='rsp_data[14]')
 assert '( PIN rsp_data[14] )' in ln
 m10=[z.strip() for z in ln.splitlines() if 'metal10' in z]
 assert m10==['NEW metal10 ( 448190 1016140 0 ) ( * 1020940 )'],m10
 out.insert(pya.Box((2288000+448190-800)*5,(144000+1016140)*5,(2288000+448190+800)*5,(144000+1020940+800)*5))

 vias={}
 for x in (p/'vias.tsv').read_text().splitlines():
  n,l,*v=x.split('\t');vias.setdefault(n,[]).append((l,list(map(int,v))))
 for m in re.finditer(r'(?:\+ ROUTED|\bNEW)\s+(\S+)\s+(.*?)(?=\bNEW|;|$)',body,re.S):
  layer,seq=m.groups();prev=None;pe=None
  for t in re.finditer(r'\(\s*(\*|-?\d+)\s+(\*|-?\d+)(?:\s+(-?\d+))?\s*\)|(\S+)',seq):
   x,y,ext,n=t.groups()
   if x is not None:
    pt=(prev[0] if x=='*' else int(x),prev[1] if y=='*' else int(y));ce=800 if ext is None else int(ext)
    if prev and layer=='metal10':
     if pt[0]==prev[0]:
      lo,hi=sorted([(prev[1],pe),(pt[1],ce)]);v=[pt[0]-800,lo[0]-lo[1],pt[0]+800,hi[0]+hi[1]]
     else:
      assert pt[1]==prev[1];lo,hi=sorted([(prev[0],pe),(pt[0],ce)]);v=[lo[0]-lo[1],pt[1]-800,hi[0]+hi[1],pt[1]+800]
     out.insert(pya.Box(*[k*5 for k in v]))
    prev=pt;pe=ce
   elif n in vias:
    for l,v in vias[n]:
     if l=='metal10':out.insert(pya.Box(*[(k+prev[i%2])*5 for i,k in enumerate(v)]))
   else:assert n in ('TAPER','+','USE','SIGNAL'),n
 return (out&roi).merged()
old=netregion(p/'before.def');new=netregion(p/'patched.def')
def component_cover(allm,target):
 comp=pya.Region()
 for poly in allm.merged().each():
  q=pya.Region(poly)
  if not (q&target).is_empty():comp+=q
 assert (comp^target).is_empty(),'unaccounted actual connected M10 geometry'
component_cover(a10,old);component_cover(b10,new)

assert (old-a10).is_empty() and (new-b10).is_empty()
assert (old-new).is_empty() and ((new-old)^added).is_empty()
assert new.count()==1,('disconnected target',new.count())
assert (added&(a10-old)).is_empty(),'foreign-net overlap'
assert (new.separation_check(a10-old,8000)).is_empty(),'foreign-net spacing'
inner=pya.Region(pya.Box(13658000,5798000,13676000,5820000))
def markers(q):return {name:[str(x) for x in e.each() if not (pya.Region(x.bbox())&inner).is_empty()] for name,e in [('space',q.space_check(8000)),('notch',q.notch_check(8000)),('width',q.width_check(8000))]}
pre=markers(a10);post=markers(b10);assert all(not v for v in post.values()),post
for l in a.layer_infos():
 if (l.layer,l.datatype)==(29,0):continue
 x=pya.Region(a.top_cell().begin_shapes_rec(a.layer(l)))&roi;y=pya.Region(b.top_cell().begin_shapes_rec(b.layer(l)))&roi
 assert (x^y).is_empty(),str(l)
res=dict(passed=True,scope='Actual regenerated GDS and independently reconstructed same-net DEF+pin M10 component. No full backend signoff.',added_area_um2=added.area()*1e-8,removed_area_um2=0,target_component_count=new.count(),actual_connected_components_exactly_covered=True,leaf_internal_m10_bound=True,foreign_net_overlap=False,foreign_net_spacing_800nm_passed=True,before=pre,after=post,other_local_layers_equal=True,hashes={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in [src,p/'patched.gds',p/'patched.odb',p/'before.def',p/'patched.def',Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-200-compact-local-s/run08-base0/results/0/flow/results/nangate45/local_s_base/base/6_final.def'),Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-200-compact-local-s/run08-base0/results/0/flow/results/nangate45/local_s_base/base/6_final.gds')]})
(p/'gds-local-receipt.json').write_text(json.dumps(res,indent=2));print(json.dumps(res,indent=2))
