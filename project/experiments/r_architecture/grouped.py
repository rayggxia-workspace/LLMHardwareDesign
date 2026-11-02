from pathlib import Path
import os,time,json
from worker import task
from strict_state import lower,prove,map_proven
from proof_selftest import selftest
out=Path.cwd()/'results';out.mkdir(exist_ok=False);r=task('A2g-rtl',out/'A2g-rtl',0);assert r['passed'];selftest(out/'proof-route-selftest')
path=lower('A2g',out);base=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture/attempt023/results/A0');
while not(base/'lowered.json').exists()or'Time spent:'not in(base/'lower.log').read_text()[-1000:]:time.sleep(15)
p=prove('A2g',{'A0':base/'lowered.json','A2g':path},out);map_proven(p,out,out/'A2g-rtl/receipt.json');assert p['passed']
