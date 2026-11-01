from pathlib import Path
from strict_state import cut
import json,collections
B=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture')
out=Path.cwd()/'results';out.mkdir(exist_ok=False)
a,al,ai,ac=cut(B/'attempt023/results/A0/lowered.json');del a
b,bl,bi,bc=cut(B/'attempt048/results/A2h/lowered.json');del b
sa,sb=set(map(tuple,al)),set(map(tuple,bl))
row=dict(gold_bits=len(al),gate_bits=len(bl),only_gold=sorted(sa-sb),only_gate=sorted(sb-sa),gold_bases=dict(collections.Counter(n.split('[')[0]for n,i in al)),gate_bases=dict(collections.Counter(n.split('[')[0]for n,i in bl)),initial_differences=[(x,y,z)for x,y,z in zip(al,ai,bi)if y!=z]if al==bl else'labels differ')
(out/'STATE_DIAGNOSTIC.json').write_text(json.dumps(row,indent=2)+'\n')
