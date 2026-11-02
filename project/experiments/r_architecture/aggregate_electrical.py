"""Recount entire mapped nonclock pin networks; no remapping or physical mutation."""
from pathlib import Path
import json,concurrent.futures,hashlib
from inventory import inventory
B=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture');O=Path.cwd()/'results';O.mkdir(exist_ok=False);LIB=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
tasks=[('A0','attempt001/results/A0-map'),('A1','attempt035/results/A1-map'),('A2','attempt051/results/A2h-map')]+[('B'+str(c),'attempt011/results/'+str(c))for c in [256,512,1024,2048]]+[('C-N-native','attempt055/unit/c_wide_native')]
def run(item):
 label,source=item;p=B/source;before=hashlib.sha256((p/'mapped.json').read_bytes()).hexdigest();data=inventory(p,LIB);assert before==hashlib.sha256((p/'mapped.json').read_bytes()).hexdigest();data['candidate']=label;(O/(label+'.json')).write_text(json.dumps(data,indent=2)+'\n');return data
with concurrent.futures.ProcessPoolExecutor(max_workers=8)as pool:rows=list(pool.map(run,tasks))
(O/'INVENTORY.json').write_text(json.dumps(rows,indent=2)+'\n')
