import pya,json,hashlib
from pathlib import Path
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117');c=root/'gs/candidate-S-minimal-localv4/parent-F-eco-h20-v4';gds=c/'qualification-diagnostic/flow/results/nangate45/f-native-frame/base/6_final.gds'
l=pya.Layout();l.read(str(gds));top=l.cell('cfj_group_f');assert top is not None
insts=[i for i in top.each_inst() if l.cell(i.cell_index).name=='local_s_base'];assert len(insts)==1
inst=insts[0];layer=l.find_layer(29,0);assert layer is not None
leaf=pya.Region(l.cell(inst.cell_index).begin_shapes_rec(layer)).transformed(inst.trans);parent=pya.Region(top.shapes(layer));report=[]
import re
for marker in json.loads((root/'audit/F-native-marker-diff.json').read_text())['added']:
 vals=re.search(r'bbox = \(([^,]+), ([^)]+)\) - \(([^,]+), ([^)]+)\) on Layer metal10',marker);assert vals
 box=pya.Box(*[round(float(x)/l.dbu) for x in vals.groups()]);region=pya.Region(box.enlarged(1))
 lh=leaf & region;ph=parent & region
 report.append(dict(marker=marker,leaf_area_um2=lh.area()*l.dbu*l.dbu,parent_area_um2=ph.area()*l.dbu*l.dbu,intersection_area_um2=(lh&ph).area()*l.dbu*l.dbu))
r=dict(passed=all(x['leaf_area_um2']==0 for x in report),scope='Every new native macro-short marker has no actual leaf M10 material in the marker expanded by 1 GDS DBU',markers=report,sha256={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in [gds,root/'audit/F-native-marker-diff.json']})
(root/'audit/F-new-marker-gds.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
