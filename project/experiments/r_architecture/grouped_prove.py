"""Complete A2h proof after explicit bijective grouped-to-flat state relabeling."""
from pathlib import Path
from strict_state import I,map_proven,sha
from partitioned_proof import prove_all,selftest
from inventory import inventory
import json
B=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture');O=Path.cwd()/'results';O.mkdir(exist_ok=False);selftest(O)
lower=B/'attempt048/results/A2h/lowered.json';assert'Time spent:'in(lower.parent/'lower.log').read_text()[-1000:]
(O/'STATE_RELATION_RULE.json').write_text(json.dumps(dict(rule='zz_state_group[g].first_bank[w] <-> bank0[64*g+w]; second_bank <-> bank1; all other state names identical, all bits included',group_range=[0,31],word_range=[0,63],state_word_bits=32,grouped_state_bits=2*32*64*32,lowered_sha256=sha(lower)),indent=2)+'\n')
proof=prove_all('A2h',{'A0':B/'attempt023/results/A0/lowered.json','A2h':lower},O,I/'candidates/A2h/block_v1_r.sv')
map_proven(proof,O,B/'attempt048/results/A2h-rtl/receipt.json');assert proof['passed']
folder=O/'A2h-map'
if json.loads((folder/'receipt.json').read_text())['passed']:(folder/'INVENTORY.json').write_text(json.dumps(inventory(folder,Path('/OpenROAD-flow-scripts/flow/platforms/nangate45/lib/NangateOpenCellLibrary_typical.lib')),indent=2)+'\n')
