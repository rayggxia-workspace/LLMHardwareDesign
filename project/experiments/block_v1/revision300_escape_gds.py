"""KLayout-only joined-scene readback; native masks stay unchanged."""
import json
from decimal import Decimal
from pathlib import Path
import pya

manifest=Path('INPUT_MANIFEST_PLACEHOLDER')
request=json.loads(manifest.read_text())
fixture=json.loads(Path(request['fixture']).read_text())
mapping={'metal10':(29,0),'via10':(210,0),'metal11':(211,0),'via11':(212,0),'metal12':(213,0)}
native=pya.Layout();native.read(request['native_gds'])
tops=native.top_cells();assert len(tops)==1
leaf=tops[0]
native_pairs={(native.get_info(i).layer,native.get_info(i).datatype) for i in native.layer_indexes()}
assert not native_pairs.intersection(set(mapping.values())-{mapping['metal10']})
dbu=Decimal(str(native.dbu))
def coordinate(value,source_dbu=2000):
    exact=Decimal(value)/Decimal(source_dbu)/dbu
    assert exact==exact.to_integral_value(),('Inexact GDS conversion',value,source_dbu,native.dbu)
    return int(exact)
def micron(value):return coordinate(value,1)
offset=micron(request['offset_um']);translation=pya.Trans(offset,offset)
wrapper=native.create_cell('REV300_ALL_PORT_ESCAPE')
assert wrapper.cell_index()!=leaf.cell_index()
wrapper.insert(pya.CellInstArray(leaf.cell_index(),translation))
expected=[]
for row in fixture['shapes']:
    if row['layer']=='metal10':continue
    pair=mapping[row['layer']];box=tuple(coordinate(v) for v in row['box_dbu'])
    shape=wrapper.shapes(native.layer(*pair)).insert(pya.Box(*box))
    shape.set_property(1,row['net']);expected.append((*pair,box,row['net']))
native.write(request['output'])
read=pya.Layout();read.read(request['output'])
assert read.dbu==native.dbu and len(read.top_cells())==1
top=read.top_cell();observed=[];regions={}
for name,pair in mapping.items():
    idx=read.layer(*pair);regions[name]=pya.Region(top.begin_shapes_rec(idx));regions[name].merge()
    if name=='metal10':continue
    for shape in top.shapes(idx).each():
        assert shape.is_box()
        b=shape.box;observed.append((*pair,(b.left,b.bottom,b.right,b.top),shape.property(1)))
assert sorted(expected)==sorted(observed),'Upper masks or net identities changed on GDS readback'
native_checks={}
for pair in sorted(native_pairs):
    before=pya.Region(leaf.begin_shapes_rec(native.layer(*pair))).transformed(translation)
    after=pya.Region(top.begin_shapes_rec(read.layer(*pair)))
    native_checks['%d/%d'%pair]=(before^after).is_empty()
    assert native_checks['%d/%d'%pair],('Native mask changed',pair)
checks={}
for name in ('metal11','metal12'):
    checks[name+'_width']=regions[name].width_check(micron(2)).is_empty()
    checks[name+'_spacing']=regions[name].space_check(micron(2)).is_empty()
for via,lower,upper in [('via10','metal10','metal11'),('via11','metal11','metal12')]:
    checks[via+'_spacing']=regions[via].space_check(micron(2.2)).is_empty()
    checks[via+'_lower_enclosure']=(regions[via]-regions[lower]).is_empty()
    checks[via+'_upper_enclosure']=(regions[via]-regions[upper]).is_empty()
    # Every cut is exactly2x2; region width alone would miss oversized cuts.
    checks[via+'_cut_size']=all(b[2]-b[0]==micron(2) and b[3]-b[1]==micron(2)
        for layer,datatype,b,net in observed if (layer,datatype)==mapping[via])
assert all(checks.values()),checks
result=dict(passed=True,native_all_mask_xor_zero=native_checks,upper_gds_identity_exact=True,
    upper_shapes=len(observed),all_signal_bits=fixture['expected_bits'],gds_dbu_um=native.dbu,
    native_translation_um=request['offset_um'],checks=checks,
    scope='Actual joined GDS readback, unchanged native masks and ideal-alignment new-layer geometric rules. Native whole-deck acceptance is separately bound; no12-layer process or timing qualification.')
(manifest.parent/'joined-readback.json').write_text(json.dumps(result,indent=2)+'\n')
