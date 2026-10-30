"""KLayout batch Python: isolated width/space fixtures, not circuit layouts."""
from pathlib import Path
import json,pya

out=Path(outdir)
fixtures={
 'wide_isolated':[(0,0,1000,1000)],
 'thin_isolated':[(0,0,150,1000)],
 'wide_gap150':[(0,0,1000,1000),(1150,0,2150,1000)],
 'wide_gap100':[(0,0,1000,1000),(1100,0,2100,1000)],
 'wide_gap250':[(0,0,1000,1000),(1250,0,2250,1000)],
 'wide_touching':[(0,0,1000,1000),(1000,0,2000,1000)]}
for name,boxes in fixtures.items():
    layout=pya.Layout();layout.dbu=.001;top=layout.create_cell('TOP');layer=layout.layer(21,0)
    for box in boxes:top.shapes(layer).insert(pya.Box(*box))
    layout.write(str(out/(name+'.gds')))
(out/'fixtures.json').write_text(json.dumps({'unit':'nm coordinates; GDS dbu0.001um','KLayout_version':pya.Application.instance().version(),'fixtures':fixtures},indent=2)+'\n')
