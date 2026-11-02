from pathlib import Path
import argparse,time,json
from partitioned_proof import prove_all,selftest
from strict_state import map_proven,I
p=argparse.ArgumentParser();p.add_argument('--candidate',choices=['A1','A2g'],default='A1');a=p.parse_args();out=Path.cwd()/'results';out.mkdir(exist_ok=False);selftest(out)
base=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture');paths={'A0':base/'attempt023/results/A0/lowered.json',a.candidate:base/('attempt023/results/A1/lowered.json'if a.candidate=='A1'else'attempt028/results/A2g/lowered.json')}
for v in paths.values():
 while not v.exists()or'Time spent:'not in(v.parent/'lower.log').read_text()[-1000:]:time.sleep(15)
receipt=prove_all(a.candidate,paths,out,I/'candidates'/a.candidate/'block_v1_r.sv');regression=I/'evidence/attempt001/results/A1-rtl/receipt.json'if a.candidate=='A1'else base/'attempt028/results/A2g-rtl/receipt.json';map_proven(receipt,out,regression);assert receipt['passed']
