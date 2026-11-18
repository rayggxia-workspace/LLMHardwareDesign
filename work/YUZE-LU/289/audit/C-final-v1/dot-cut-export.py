import pya,json,hashlib
from pathlib import Path
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');out=root/'audit/C-final-v1/macro-obs-v20';master='e_s32_pipeline_128'
cov=json.loads((out/'coverage.json').read_text());rows=[x for x in cov['rows'] if x['master']==master];assert len(rows)==4;gds=Path(rows[0]['gds']);rawsha=hashlib.sha256(gds.read_bytes()).hexdigest();assert rawsha==cov['source_sha256'][str(gds)]
layout=pya.Layout();layout.read(str(gds));cell=layout.cell(master);assert cell
lines=[];counts={};areas={}
for layer,n in (('via6',22),('via7',24),('via8',26),('via9',28)):
 region=pya.Region(cell.begin_shapes_rec(layout.layer(n,0)));boxes=set();sum_area=0
 for shape in region.each():
  box=shape.bbox();assert shape.area()==box.area(),('Nonrectangular actualcut',layer,str(box))
  coords=[v*layout.dbu*2000 for v in (box.left,box.bottom,box.right,box.top)];assert all(abs(v-round(v))<1e-5 for v in coords);boxes.add(tuple(map(round,coords)))
 for box in sorted(boxes):lines.append('\t'.join(map(str,[master,layer,*box])))
 counts[layer]=len(boxes);areas[layer]=region.area()*layout.dbu**2
path=out/'dot-actual-cut-obs.tsv';assert not path.exists();path.write_text('\n'.join(lines)+'\n')
r=dict(scope='Read-only exact native rectangular source cut geometry, no inflation or pin/macro edits. Subsequent injection/DRC qualification remains separate.',master=master,dbu_per_micron=2000,gds_dbu_micron=layout.dbu,cut_counts=counts,source_area_um2=areas,columns=['master','layer','xmin_dbu','ymin_dbu','xmax_dbu','ymax_dbu'],source_sha256={str(gds):rawsha,str(path):hashlib.sha256(path.read_bytes()).hexdigest(),str(Path(__file__)):hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},all_actual_cuts_rectangular=True)
(out/'dot-actual-cut-binding.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
