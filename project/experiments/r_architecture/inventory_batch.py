from pathlib import Path
import json,concurrent.futures
from inventory import inventory
BASE=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture')
LIB=Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')
OUT=Path.cwd()/'results';OUT.mkdir(exist_ok=False)
tasks=[('A0',BASE/'attempt001/results/A0-map')]+[('B'+str(c),BASE/('attempt011/results/'+str(c)))for c in [256,512,1024,2048]]+[('C-wide',BASE/'attempt009/results/c_wide_m'),('C-finish',BASE/'attempt009/results/c_finish')]+[(k,BASE/('attempt012/results/'+k))for k in ['block_v2_m','block_v2_e','block_feed_s16k']]+[('txn_ctrl',BASE/'attempt013/results/txn_ctrl')]
def run(t):
 k,f=t;r=inventory(f,LIB);r['candidate']=k;(OUT/(k+'.json')).write_text(json.dumps(r,indent=2)+'\n');return r
with concurrent.futures.ThreadPoolExecutor(max_workers=4)as pool:rows=list(pool.map(run,tasks))
(OUT/'INVENTORY.json').write_text(json.dumps(rows,indent=2)+'\n')
