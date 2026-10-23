"""Native OpenDB inventory and access API discovery, no source mutation."""
import collections
import json
from pathlib import Path
import odb

root = Path.cwd()
args = json.loads((root/'inputs.json').read_text())
db = odb.dbDatabase.create()
odb.read_db(db,args['odb'])
b = db.getChip().getBlock()
inventory = []
for inst in b.getInsts():
    inventory.append(dict(name=inst.getName(),master=inst.getMaster().getName(),
        xy=list(inst.getLocation()),orient=str(inst.getOrient()),status=str(inst.getPlacementStatus()),
        pins={p.getMTerm().getName():p.getNet().getName() if p.getNet() else None for p in inst.getITerms()}))
(root/'active-inventory.json').write_text(json.dumps(sorted(inventory,key=lambda i:i['name']),indent=2)+'\n')
types = collections.Counter(i['master'] for i in inventory)
print('MASTER_COUNTS',json.dumps(types,sort_keys=True))
for obj in [odb.dbWireDecoder,odb.dbWireEncoder,odb.dbWire,odb.dbITerm,odb.dbBTerm,odb.dbNet]:
    print('API',obj.__name__,[x for x in dir(obj) if not x.startswith('_')])
clock = [n for n in b.getNets() if str(n.getSigType()) == 'CLOCK']
print('CLOCK_NETS',len(clock),[n.getName() for n in clock])
print('DBU',b.getDbUnitsPerMicron())
print('LAYERS',[(l.getName(),l.getRoutingLevel(),l.getType()) for l in db.getTech().getLayers()])
(root/'inventory-summary.json').write_text(json.dumps(dict(instances=len(inventory),masters=types,clock_nets=len(clock)),indent=2)+'\n')
