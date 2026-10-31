"""Executed by KLayout, independent of the Python fixture graph verifier."""
import json
from pathlib import Path
import pya

manifest=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121/block-v1-20261030-404/tasks/revision300-route-r/fixtures.json')
mapping={'metal10':(29,0),'via10':(210,0),'metal11':(211,0),'via11':(212,0),'metal12':(213,0)}
results=[]
for entry in json.loads(manifest.read_text()):
    source=json.loads(Path(entry['json_path']).read_text())
    layout=pya.Layout();layout.dbu=1/source['dbu_per_um'];cell=layout.create_cell(entry['name'])
    expected=[]
    for s in source['shapes']:
        layer,datatype=mapping[s['layer']];box=list(s['box_dbu'])
        shape=cell.shapes(layout.layer(layer,datatype)).insert(pya.Box(*box));shape.set_property(1,s['net'])
        expected.append((layer,datatype,tuple(box),s['net']))
    layout.write(entry['gds_path'])
    actual=pya.Layout();actual.read(entry['gds_path']);top=actual.top_cell();observed=[];regions={}
    assert actual.dbu==layout.dbu
    for name,pair in mapping.items():
        index=actual.layer(*pair);regions[name]=pya.Region(top.begin_shapes_rec(index));regions[name].merge()
        for s in top.shapes(index).each():
            assert s.is_box();b=s.box
            observed.append((pair[0],pair[1],(b.left,b.bottom,b.right,b.top),s.property(1)))
    assert sorted(observed)==sorted(expected),'Actual GDS identity/geometry differs'
    checks={}
    for name in ('metal10','metal11','metal12'):
        value=1600 if name=='metal10'else 4000
        checks[name+'_width']=regions[name].width_check(value).is_empty()
        checks[name+'_spacing']=regions[name].space_check(value).is_empty()
    for via,lo,hi in [('via10','metal10','metal11'),('via11','metal11','metal12')]:
        checks[via+'_spacing']=regions[via].space_check(4400).is_empty()
        checks[via+'_lower_enclosure']=(regions[via]-regions[lo]).is_empty()
        checks[via+'_upper_enclosure']=(regions[via]-regions[hi]).is_empty()
    assert all(checks.values()),(entry['name'],checks)
    results.append(dict(name=entry['name'],passed=True,gds_readback_exact=True,checks=checks,gds_bytes=Path(entry['gds_path']).stat().st_size))
(manifest.parent/'klayout-results.json').write_text(json.dumps(dict(passed=True,fixtures=results,scope='Independent actual GDS rectangle identity, nativeM10 limited width/space and new-layer width/space/cut-enclosure; not complete native-macro DRC.'),indent=2)+'\n')
