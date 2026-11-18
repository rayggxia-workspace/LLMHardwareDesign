from pathlib import Path
import pya,re,json,hashlib
r=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');p=r/'audit/C-v28-upper-patch-v2';meta=r/'audit/C-v28-i8h50-physical/rcx-material-120132';src=r/'cu/runs/C-v28-actual-i8-h50/flow/results/nangate45/c-overlay-current/base'
cases=[('net118438',[1885,487,1893,495]),('net73253',[1389,673,1397,681]),(r'services.engine\[0\].element.e32.aperture_data\[68\]',[2022,828,2030,837]),(r'services.engine\[0\].element.arithmetic.out_data\[62\]',[1371,908,1378,915])]
widths={n:int(w) for n,w in [x.split() for x in (meta/'layers.tsv').read_text().splitlines()]};vias={}
for x in (meta/'vias.tsv').read_text().splitlines():
 n,l,*v=x.split();vias.setdefault(n,[]).append((l,list(map(int,v))))
def nets(f):
 s=f.read_text().split('\nNETS ',1)[1].split('\nEND NETS',1)[0];return {x.split()[0]:x for x in re.split(r'(?m)^\s*-(?= )',s)[1:]}
old=nets(p/'before.def');new=nets(p/'patched.def');assert set(old)==set(new)
assert {n for n in old if old[n]!=new[n]}=={n for n,b in cases}
def geometry(text,layer):
 out=pya.Region()
 for m in re.finditer(r'(?:\+ ROUTED|\bNEW)\s+(\S+)\s+(.*?)(?=\bNEW|;|$)',text,re.S):
  lay,seq=m.groups();prev=None;pe=None
  for t in re.finditer(r'\(\s*(\*|-?\d+)\s+(\*|-?\d+)(?:\s+(-?\d+))?\s*\)|(\S+)',seq):
   x,y,ext,n=t.groups();boxes=[]
   if x is not None:
    pt=(prev[0] if x=='*' else int(x),prev[1] if y=='*' else int(y));half=widths[lay]//2;ce=half if ext is None else int(ext)
    if prev and lay==layer:
     if pt[0]==prev[0]:lo,hi=sorted([(prev[1],pe),(pt[1],ce)]);v=[pt[0]-half,lo[0]-lo[1],pt[0]+half,hi[0]+hi[1]]
     else:
      assert pt[1]==prev[1];lo,hi=sorted([(prev[0],pe),(pt[0],ce)]);v=[lo[0]-lo[1],pt[1]-half,hi[0]+hi[1],pt[1]+half]
     boxes.append(v)
    prev=pt;pe=ce
   elif n in vias:boxes += [[v+prev[i%2] for i,v in enumerate(box)] for l,box in vias[n] if l==layer]
   for box in boxes:out.insert(pya.Box(*[v*5 for v in box]))
 return out.merged()
a=pya.Layout();a.read(str(src/'6_final.gds'));b=pya.Layout();b.read(str(p/'patched.gds'));assert a.dbu==b.dbu==.0001
def region(lay,li,box):
 q=pya.DBox((box.left-1)*lay.dbu,(box.bottom-1)*lay.dbu,(box.right+1)*lay.dbu,(box.top+1)*lay.dbu)
 return (pya.Region(lay.top_cell().begin_shapes_rec_touching(li,q))&pya.Region(box)).merged()
reports=[];layers={27:'metal9',28:'via9',29:'metal10'}
for name,bbox in cases:
 box=pya.Box(*[round(v*10000) for v in bbox]);roi=pya.Region(box);changed=[]
 for info in a.layer_infos():
  aa=region(a,a.layer(info),box);bb=region(b,b.layer(info),box)
  if info.layer in layers and info.datatype==0:
   layer=layers[info.layer];o=geometry(old[name],layer)&roi;n=geometry(new[name],layer)&roi
   assert (o-aa).is_empty() and (n-bb).is_empty(),(name,layer,'missing top material')
   delta=(((aa-o)+n)^bb).merged()
   assert delta.is_empty(),(name,layer,'unexpected GDS material delta',str(delta),delta.area())
   added=bb-aa;removed=aa-bb
   if not added.is_empty() or not removed.is_empty():
    foreign=aa-o
    assert (added&foreign).is_empty(),(name,layer,'foreign contact')
    distance=8800 if layer=='via9' else 8000
    assert n.separation_check(foreign,distance).is_empty(),(name,layer,'foreign spacing')
    assert n.space_check(distance).is_empty(),(name,layer,'internal space')
    if layer!='via9':assert n.notch_check(8000).is_empty() and n.width_check(8000).is_empty(),(name,layer,'width/notch')
    changed.append(dict(layer=layer,added_um2=added.area()*1e-8,removed_um2=removed.area()*1e-8))
  else:assert (aa^bb).is_empty(),(name,str(info),'unintended layer change')
 reports.append(dict(net=name,actual_material_exact=True,foreign_spacing_contact_passed=True,changed=changed));print('PASS',name,flush=True)
files=[src/'6_final.gds',src/'6_final.odb',p/'before.def',p/'patched.def',p/'patched.odb',p/'patched.gds',meta/'vias.tsv',meta/'layers.tsv',Path(__file__)]
receipt=dict(passed=True,backend_accepted=False,scope='Four localized parent wire edits; exact actual GDS material deltas, unchanged other local layers and foreign contact/spacing plus M9/M10 width/notch and V9 880nm spacing. Full unchanged deck and re-extracted timing remain required.',cases=reports,hashes={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in files})
(p/'gds-local-receipt.json').write_text(json.dumps(receipt,indent=2))
