"""Inspect actual hierarchy handles from a retained failed extraction."""
import json
import os
from pathlib import Path
import pya

root=Path(os.environ['ROUTER_INSPECT_ROOT'])
l2n=pya.LayoutToNetlist();l2n.read(str(root/'attempt32/topology/native.l2n'))
inventory=json.loads((root/'attempt32/inventory.json').read_text())
print('TOP_CIRCUITS',[(c.name,c.cell_index) for c in l2n.netlist().top_circuits()],flush=True)
for name,term in inventory['terms'].items():
    if term['signal_type']!='SIGNAL':continue
    for shape in term['shapes']:
        if shape['layer']!='metal10':continue
        a,b,c,d=shape['rect'];point=pya.DPoint((a+c)/4000,(b+d)/4000)
        path=[];net=l2n.probe_net(l2n.layer_by_name('metal10'),point,path)
        print('PROBE',name,str(point),net.circuit().name,net.cluster_id,
              [(None if s is None else [s.name,s.circuit_ref().name,str(s.trans)]) for s in path],flush=True)
        if None in path:
            print('CIRCUIT',net.circuit().to_s(),flush=True)
            raise RuntimeError('retained null hierarchy handles for investigation')
    break
