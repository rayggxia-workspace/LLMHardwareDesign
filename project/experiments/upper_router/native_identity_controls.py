"""Positive and adversarial controls for exact hierarchical native readback."""
import json
import os
from pathlib import Path
import sys
import pya
sys.path.insert(0,str(Path(__file__).resolve().parent))
from native_identity import verify


def layout():
    l=pya.Layout();l.dbu=.001;top=l.create_cell('native');leaf=l.create_cell('leaf')
    leaf.shapes(l.layer(29,0)).insert(pya.Box(0,0,20,20))
    top.insert(pya.CellInstArray(leaf.cell_index(),pya.Trans(40,60)))
    return l


reference=layout();candidate=layout();top=candidate.top_cell();upper=candidate.create_cell('upper')
top.insert(pya.CellInstArray(upper.cell_index(),pya.Trans()))
assert verify(reference,candidate,'upper')['passed']
results={'unchanged_hierarchy':True}
for mutation in ('leaf_geometry','instance_placement','missing_native_cell','database_grid'):
    changed=candidate.dup()
    if mutation=='leaf_geometry':changed.cell('leaf').shapes(changed.layer(29,0)).insert(pya.Box(20,0,21,20))
    elif mutation=='instance_placement':
        inst=next(i for i in changed.cell('native').each_inst() if i.cell.name=='leaf');inst.trans=pya.Trans(41,60)
    elif mutation=='missing_native_cell':changed.cell('leaf').name='different_leaf'
    else:changed.dbu=.0005
    try:verify(reference,changed,'upper')
    except AssertionError:results[mutation+'_rejected']=True
    else:raise RuntimeError('changed native geometry accepted: '+mutation)
output=Path(os.environ['ROUTER_IDENTITY_CONTROLS'])
output.write_text(json.dumps({'passed':True,'controls':results},indent=2)+'\n');print(json.dumps(results),flush=True)
