"""Resolve only demonstrably filled same-net checker markers; never a waiver.

Each whole marker must be covered by that same net's real ODB route segments
AND by actual GDS metal. Multi-net spacing, uncovered gaps and other types fail.
The original full GDS DRC must independently pass after this proof.
"""
import hashlib, json
from pathlib import Path
import pya

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

directory=Path(DIRECTORY)
rows=[x.split('\t') for x in (directory/'marker-input.tsv').read_text().splitlines()]
shapes={int(row[0]):pya.Region() for row in rows}
for line in (directory/'marker-shapes.tsv').read_text().splitlines():
    index,*coords=map(int,line.split('\t'));shapes[index].insert(pya.Box(*coords))
layout=pya.Layout();layout.read(str(GDS));top=layout.top_cell();assert top.name=='mother_control_64'
regions={};results=[]
for index,name,layer,*coords in rows:
    raw=list(map(int,coords));box=pya.Box(*raw)
    same_net=(pya.Region(box)-shapes[int(index)].merged()).is_empty()
    level=int(layer.removeprefix('metal'));assert level in (2,3)
    # FreePDK45 native stream map: M1=11/0, M2=13/0, ..., M10=29/0.
    stream=9+2*level
    if level not in regions:regions[level]=pya.Region(top.begin_shapes_rec(layout.layer(stream,0))).merged()
    scale=1/2000/layout.dbu;gds_box=pya.Box(*[round(v*scale) for v in raw])
    copper=(pya.Region(gds_box)-regions[level]).is_empty()
    outside=top.bbox();control=pya.Box(outside.right+10000,outside.top+10000,outside.right+12000,outside.top+12000)
    assert not (pya.Region(control)-regions[level]).is_empty()
    results.append(dict(index=int(index),net=name,layer=layer,box_dbu=raw,
        same_net_odb_route_fills_entire_marker=same_net,actual_gds_fills_entire_marker=copper,passed=same_net and copper))
report=dict(schema='mother-native-filled-marker-proof/1',passed=all(x['passed'] for x in results),
    results=results,outside_negative_control=True,original_report_sha256=sha(directory/'native-drc.rpt'),
    gds_sha256=sha(GDS),input_sha256=sha(directory/'marker-input.tsv'),route_shapes_sha256=sha(directory/'marker-shapes.tsv'),
    scope='Only fully filled same-net regions resolved; original report retained; original full GDS deck still required')
(directory/'marker-proof.json').write_text(json.dumps(report,indent=2)+'\n')
assert report['passed'],report
