import pya,json,math,hashlib
from pathlib import Path
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117')
gds=root/'cu/runs/U-v13-electrical-f50-x4/flow/results/nangate45/u-overlay-current/base/6_final.gds'
layout=pya.Layout();layout.read(str(gds))
out=root/'u-physical/leaf-cut-obs.tsv'
counts={}
with out.open('w') as f:
 for name in ['local_s_base','block_v2_e_compact']:
  cell=layout.cell(name);assert cell is not None
  for num,layer in [(24,'via7'),(26,'via8'),(28,'via9')]:
   index=layout.find_layer(num,0);assert index is not None
   region=pya.Region(cell.begin_shapes_rec(index));region.merge()
   count=0
   for polygon in region.each():
    assert polygon.is_box(),(name,layer,'nonrectangular cut material')
    b=polygon.bbox();vals=[b.left,b.bottom,b.right,b.top]
    coords=[math.floor(v*layout.dbu*2000+1e-7) if i<2 else math.ceil(v*layout.dbu*2000-1e-7) for i,v in enumerate(vals)]
    f.write('\t'.join(map(str,[name,layer,*coords]))+'\n');count+=1
   counts[name+'/'+layer]=count
r=dict(scope='actual leaf cut material as conservative routing OBS; no GDS geometry changed',counts=counts,gds_sha256=hashlib.sha256(gds.read_bytes()).hexdigest(),tsv_sha256=hashlib.sha256(out.read_bytes()).hexdigest())
(out.parent/'leaf-cut-obs.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
