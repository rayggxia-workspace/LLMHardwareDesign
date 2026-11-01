from pathlib import Path
import json,concurrent.futures,time
from inventory import inventory
BASE=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture');LIB=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib');OUT=Path.cwd()/'results';OUT.mkdir(exist_ok=False)
tasks=[('A0',BASE/'attempt001/results/A0-map'),('A1',BASE/'attempt035/results/A1-map')]+[('B'+str(c),BASE/('attempt011/results/'+str(c)))for c in [256,512,1024,2048]]+[('C-E-wide',BASE/'attempt037/results/c_wide_e')]
def run(t):
 k,p=t;r=inventory(p,LIB);r['candidate']=k;(OUT/(k+'.json')).write_text(json.dumps(r,indent=2)+'\n');return r
with concurrent.futures.ProcessPoolExecutor(max_workers=6)as pool:rows=list(pool.map(run,tasks))
(OUT/'INVENTORY.json').write_text(json.dumps(rows,indent=2)+'\n')
proof=BASE/'attempt036/results/A2g-full-proof/receipt.json'
while not proof.exists():time.sleep(15)
r=json.loads(proof.read_text())
if r['passed']:
 mapped=BASE/'attempt036/results/A2g-map/receipt.json'
 while not mapped.exists():time.sleep(15)
 r=json.loads(mapped.read_text())
 if r['passed']:rows.append(run(('A2g',mapped.parent)));(OUT/'INVENTORY.json').write_text(json.dumps(rows,indent=2)+'\n')
(OUT/'A2_ELIGIBILITY.json').write_text(json.dumps(r,indent=2)+'\n')
