"""Preserve the independent stock geometry check while admitting B's explicit arcs."""
import hashlib
import json
from pathlib import Path
import runpy
import sys

import check


verifier, manifest = sys.argv[1:3]
arguments = sys.argv[3:]
src = json.loads(Path(arguments[1]).read_bytes())
tech = src['technology']
ox, oy = tech['origin']
step = tech['access_pitch']
segments = set()
vias = set()


def line_key(a,b):
    return tuple(sorted((tuple(a),tuple(b))))


if manifest != '-':
    for line in Path(manifest).read_text().splitlines():
        x,y,layer,xx,yy,other = map(int,line.split())
        a,b = (ox+x*step,oy+y*step), (ox+xx*step,oy+yy*step)
        if layer==other:
            assert (layer==0 and y==yy and x<xx) or (layer==1 and x==xx and y<yy)
            segments.add(line_key(a,b))
        else:
            assert layer==0 and other==1 and a==b
            vias.add(a)

    StockGrid = check.RoutingGrid

    class CandidateGrid(StockGrid):
        def allows(self,a,b):
            if super().allows(a,b):
                return True
            return tuple(a) in vias if a==b else line_key(a,b) in segments

    check.RoutingGrid = CandidateGrid

sys.argv = [verifier]+arguments
runpy.run_path(verifier,run_name='__main__')
if arguments[0]=='verify':
    output = Path(arguments[3])
    result = json.loads(output.read_bytes())
    assert result['geometry_check']['passed']
    result['candidate_sha256'] = None if manifest=='-' else hashlib.sha256(Path(manifest).read_bytes()).hexdigest()
    output.write_text(json.dumps(result,sort_keys=True,separators=(',',':'))+'\n')
