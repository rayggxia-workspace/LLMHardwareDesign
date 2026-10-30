"""KLayout actual DEF conductor consumption and GDS roundtrip, not invented GDS."""
from pathlib import Path
import json,hashlib
import pya
q=json.loads(Path(spec).read_text());out=Path(q['output'])
tech=pya.Technology();tech.load('/OpenROAD-flow-scripts/flow/platforms/nangate45/FreePDK45.lyt')
options=tech.load_layout_options;options.lefdef_config.read_lef_with_def=False
options.lefdef_config.lef_files=[q['tech_lef'],'/OpenROAD-flow-scripts/flow/platforms/nangate45/lef/NangateOpenCellLibrary.macro.mod.lef']
layout=pya.Layout();layout.read(q['def'],options);top=layout.top_cell()
info={str(layout.get_info(i)):i for i in layout.layer_indices()}
(out/'actual_reader_layers.json').write_text(json.dumps(info,indent=2)+'\n')
matches=[i for i in layout.layer_indices() if layout.get_info(i).name=='metal5']
assert len(matches)==1,('Actual native DEF reader M5 mapping not unique',info)
layer=matches[0];m5info=layout.get_info(layer)
reg=pya.Region(top.begin_shapes_rec(layer));reg.merge()
results={}
for name,box in [('POINT_PAIR',(99860,99860,100140,100140)),('NONZERO_ZEROEXT',(119860,99860,120140,100140))]:
    # Layout DBU is read explicitly; expected geometry is expressed in um.
    um=(99.93,99.93,100.07,100.07) if name=='POINT_PAIR' else (119.93,99.93,120.07,100.07)
    target=pya.Box(*[round(v/layout.dbu) for v in um]);wanted=pya.Region(target)
    results[name]={'DBU':layout.dbu,'expected_box':str(target),'exact_expected_metal_present':(wanted-reg).is_empty(),'local_extra_metal':not ((reg & pya.Region(target.enlarged(round(.1/layout.dbu))))-wanted).is_empty()}
layout.write(str(out/'actual_reader_roundtrip.gds'));again=pya.Layout();again.read(str(out/'actual_reader_roundtrip.gds'))
reg2=pya.Region(again.top_cell().begin_shapes_rec(again.find_layer(m5info.layer,m5info.datatype)));reg2.merge()
assert layout.dbu==again.dbu and (reg^reg2).is_empty()
result={'scope':'ACTUAL_NATIVE_DEF_TO_KLAYOUT_GDS_CONSUMER_TEST_NOT_FAKE_SRAM_GDS_OR_FULL_DRC','klayout_version':pya.__version__,'source_DEF_SHA256':hashlib.sha256(Path(q['def']).read_bytes()).hexdigest(),'actual_reader_M5_layer':str(m5info),'methods':results,'all_M5_GDS_roundtrip_XOR_empty':True,'full_qualification':False}
(out/'stream.json').write_text(json.dumps(result,indent=2)+'\n')
