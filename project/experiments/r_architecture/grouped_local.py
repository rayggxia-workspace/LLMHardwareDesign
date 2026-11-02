"""A2h: local 64-word memory read ports; flat aliases are state labels only."""
from pathlib import Path
from worker import task
from strict_state import lower,I,map_proven
from partitioned_proof import prove_all,selftest
from inventory import inventory
import json
out=Path.cwd()/'results';out.mkdir(exist_ok=False)
r=task('A2h-rtl',out/'A2h-rtl',0);assert r['passed'];selftest(out)
p=lower('A2h',out);base=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture')
proof=prove_all('A2h',{'A0':base/'attempt023/results/A0/lowered.json','A2h':p},out,I/'candidates/A2h/block_v1_r.sv')
map_proven(proof,out,out/'A2h-rtl/receipt.json');assert proof['passed']
folder=out/'A2h-map'
if json.loads((folder/'receipt.json').read_text())['passed']:
 (folder/'INVENTORY.json').write_text(json.dumps(inventory(folder,Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')),indent=2)+'\n')

