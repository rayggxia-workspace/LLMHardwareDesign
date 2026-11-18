import pya,json,re,hashlib
from pathlib import Path
root=Path('/public/home/yuzelu/project-circuit/issue289-ab-x8-20261117/audit/U-antenna');lib=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/gds/NangateOpenCellLibrary.gds')
l=pya.Layout();l.read(str(lib));c=l.cell('ANTENNA_X1');assert c
reg=lambda i:pya.Region(c.begin_shapes_rec(l.find_layer(i,0)))
diode=(reg(4)&reg(1))-reg(3);contact=reg(10);m1=reg(11).merged();a=pya.Region(pya.Box(*[round(v/l.dbu) for v in (.06,.42,.13,.75)]))
connections=[]
for poly in m1.each():
 component=pya.Region(poly)
 if (component&a).is_empty():continue
 ct=component&contact;diff=ct&diode
 connections.append(dict(metal_component=str(poly),contact_area_um2=ct.area()*l.dbu*l.dbu,diode_contact_area_um2=diff.area()*l.dbu*l.dbu))
o=dict(passed=not diode.is_empty() and bool(connections) and all(x['diode_contact_area_um2']>0 for x in connections),cell='ANTENNA_X1',signal_pin='A',diode_definition='(nplus & active) - nwell; exact foundry deck definition',diode_area_um2=diode.area()*l.dbu*l.dbu,signal_connections=connections,gds_sha256=hashlib.sha256(lib.read_bytes()).hexdigest(),lef_signal_pin_um=[.06,.42,.13,.75],lef_ANTENNADIFFAREA=0.0,scope='Actual A-M1-contact-diode connectivity; OpenROAD LEF antenna diffarea=0 does not represent this foundry geometry')
(root/'diode-model.json').write_text(json.dumps(o,indent=2));print(json.dumps(o,indent=2));assert o['passed']
