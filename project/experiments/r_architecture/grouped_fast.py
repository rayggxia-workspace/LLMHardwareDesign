"""Same A2g RTL; formal lowering omits the pathological opt_muxtree pass.
No proof obligations are omitted. Liberty mapping remains the frozen original script.
"""
from pathlib import Path
from strict_state import run,I,map_proven
from partitioned_proof import prove_all,selftest
import time
out=Path.cwd()/'results';out.mkdir(exist_ok=False);selftest(out)
folder=out/'A2g';folder.mkdir();src=I/'candidates/A2g/block_v1_r.sv'
passes='opt_expr\nopt_merge\nopt_reduce\nopt_merge\nopt_share\nopt_dff\nopt_clean\nopt_expr\n'
run(f'read_verilog -sv {src}\nhierarchy -check -top block_v1_r\nproc\n'+passes*2+'memory_share -nowiden\nmemory_collect\nmemory_map\nopt -fast\ndffunmap\nopt_clean -purge\nwrite_json lowered.json\n',folder,'lower')
base=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture')
paths={'A0':base/'attempt023/results/A0/lowered.json','A2g':folder/'lowered.json'}
p=prove_all('A2g',paths,out,src)
map_proven(p,out,base/'attempt028/results/A2g-rtl/receipt.json')
assert p['passed']
