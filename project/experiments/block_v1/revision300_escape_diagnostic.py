"""Read existing GDS files and report XOR details without writing either."""
import json
from pathlib import Path
import pya

request=json.loads(Path('INPUT_MANIFEST_PLACEHOLDER').read_text())
native=pya.Layout();native.read(request['native_gds'])
joined=pya.Layout();joined.read(request['output'])
assert native.dbu==joined.dbu
shift=round(request['offset_um']/native.dbu);trans=pya.Trans(shift,shift)
original=native.top_cell();top=joined.top_cell();rows=[]
for idx in native.layer_indexes():
    info=native.get_info(idx);pair=(info.layer,info.datatype)
    before=pya.Region(original.begin_shapes_rec(idx)).transformed(trans)
    after=pya.Region(top.begin_shapes_rec(joined.layer(*pair)))
    difference=before^after
    if difference.is_empty():continue
    sample=[]
    for polygon in difference.each():
        sample.append(str(polygon))
        if len(sample)==4:break
    native_sample=[]
    for shape in original.shapes(idx).each():
        native_sample.append(str(shape))
        if len(native_sample)==4:break
    rows.append(dict(pair=pair,before_bbox=str(before.bbox()),after_bbox=str(after.bbox()),xor_bbox=str(difference.bbox()),
        before_count=before.count(),after_count=after.count(),xor_count=difference.count(),xor_sample=sample,native_top_shapes=native_sample))
Path('OUTPUT_REPORT_PLACEHOLDER').write_text(json.dumps(dict(native_top=original.name,joined_top=top.name,dbu=native.dbu,differences=rows),indent=2)+'\n')
