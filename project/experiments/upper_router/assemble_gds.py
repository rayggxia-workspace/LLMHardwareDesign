"""KLayout: compose immutable native source patches at algorithmic positions.

Each template is copied once; instance translations preserve the independent
leaf cells and the existing M1--M10 wires. No physical Block hard macro is made.
"""
import hashlib
import json
import os
from pathlib import Path
import pya


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(4<<20),b''):h.update(b)
    return h.hexdigest()


base_file=Path(os.environ['ROUTER_ASSEMBLY_BASE']);base=json.loads(base_file.read_text())
out=Path(os.environ['ROUTER_ASSEMBLY_OUT']);out.mkdir()
layout=pya.Layout();top=layout.create_cell('NATIVE_RESOURCE_ASSEMBLY')
templates={};inputs={}
for assembly in base['assemblies']:
    template=assembly['template'];ref=base['views'][assembly['views']['gds']]
    assert sha(ref['path'])==ref['sha256']
    if template not in templates:
        source=pya.Layout();source.read(ref['path'])
        if not templates:layout.dbu=source.dbu
        assert abs(source.dbu-layout.dbu)<1e-12,'explicit GDS rescaling required'
        original_top=source.top_cell()
        for cell in source.each_cell():cell.name='SRC_'+template+'_'+cell.name
        dest=layout.create_cell('RESOURCE_'+template);dest.copy_tree(original_top)
        templates[template]=dest.cell_index();inputs[template]=ref
        source._destroy()
    conversion=base['dbu_per_micron']*layout.dbu
    coords=[v/conversion for v in assembly['translation_dbu']]
    assert all(abs(v-round(v))<1e-8 for v in coords),'assembly translation rounds on GDS grid'
    top.insert(pya.CellInstArray(templates[template],pya.Trans(*(round(v) for v in coords))))
output=out/'native.gds';layout.write(str(output))
result={'base_file_sha256':sha(base_file),'sources':inputs,'native_gds_sha256':sha(output),
        'instances':len(base['assemblies']),'independent_leaves':len(base['leaf_instances']),
        'scope':'hierarchical native GDS assembly; actual merged ODB/netlist and RC are separate views/gates'}
(out/'assembly.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
