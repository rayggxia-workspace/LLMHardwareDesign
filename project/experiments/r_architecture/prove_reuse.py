"""Start each complete proof as soon as its exact lowered inputs exist."""
from pathlib import Path
import hashlib,json,argparse
from strict_state import prove,map_proven
from proof_selftest import selftest
import time
BASE=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture/attempt023/results')
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--candidate',choices=['A1','A2'],default='A1');a=p.parse_args();a.out.mkdir(exist_ok=False)
selftest(a.out/'proof-route-selftest')
paths={k:BASE/k/'lowered.json'for k in ['A0',a.candidate]}
for k,v in paths.items():
 while not v.exists()or 'Time spent:'not in (BASE/k/'lower.log').read_text()[-1000:]:time.sleep(15)
(a.out/'LOWERED_INPUTS.json').write_text(json.dumps({k:dict(path=str(v),sha256=hashlib.sha256(v.read_bytes()).hexdigest())for k,v in paths.items()},indent=2))
r=prove(a.candidate,paths,a.out);map_proven(r,a.out);print(json.dumps(r,indent=2));assert r['passed']
