import pya,json,hashlib
from pathlib import Path
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');c=root/'gs/candidate-S-minimal-localv4/parent-F-eco-h20-v4';gds=c/'qualification-final/flow/results/nangate45/f-native-frame/base/6_final.gds'
l=pya.Layout();l.read(str(gds));top=l.cell('cfj_group_f');assert top is not None
insts=[i for i in top.each_inst() if l.cell(i.cell_index).name=='local_s_base'];assert len(insts)==1
inst=insts[0];layer=l.find_layer(29,0);assert layer is not None
leaf=pya.Region(l.cell(inst.cell_index).begin_shapes_rec(layer)).transformed(inst.trans);parent=pya.Region(top.shapes(layer));report=[]
import re,sys
sys.path.insert(0,str(root/'audit'))
from compare_lef import parse
pins=parse(c.parent/'parent-abstract-v3/local_s_base.lef')['pins']
merged=leaf.merged()
for marker in json.loads((root/'audit/F-native-marker-diff.json').read_text())['added']:
 vals=re.search(r'bbox = \(([^,]+), ([^)]+)\) - \(([^,]+), ([^)]+)\) on Layer metal10',marker);assert vals
 box=pya.Box(*[round(float(x)/l.dbu) for x in vals.groups()]);region=pya.Region(box.enlarged(1))
 lh=leaf & region;ph=parent & region
 expected='req_addr[3]' if 'net12230 ' in marker else 'rsp_data[115]'
 total=lh&ph;covered=pya.Region();parts=[]
 for polygon in merged.each():
  component=pya.Region(polygon);actual=component&ph&region
  if actual.is_empty():continue
  connected=[]
  for name,boxes in pins.items():
   for metal,*rect in boxes:
    if metal!='metal10':continue
    pinbox=pya.Box(*[round(v/2000/l.dbu) for v in rect]).transformed(inst.trans)
    if not (component&pya.Region(pinbox)).is_empty():connected.append(name);break
  covered+=actual
  parts.append(dict(connected_leaf_pins=connected,own_pin_only=connected==[expected],intersection_area_um2=actual.area()*l.dbu*l.dbu,component_bbox=str(polygon.bbox())))
 uncovered=total-covered
 report.append(dict(expected_pin=expected,own_pin_only=bool(parts) and all(x['own_pin_only'] for x in parts) and uncovered.is_empty(),marker=marker,components=parts,total_intersection_area_um2=total.area()*l.dbu*l.dbu,covered_intersection_area_um2=covered.area()*l.dbu*l.dbu,uncovered_area_um2=uncovered.area()*l.dbu*l.dbu))

r=dict(passed=all(x['own_pin_only'] for x in report),scope='Every actual parent/leaf M10 intersection component independently connects only to expected macro pin, and exact intersection coverage is complete; unlabeled components fail',markers=report,sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [gds,root/'audit/F-native-marker-diff.json']})
(root/'audit/F-new-marker-gds-connectivity-v2.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
