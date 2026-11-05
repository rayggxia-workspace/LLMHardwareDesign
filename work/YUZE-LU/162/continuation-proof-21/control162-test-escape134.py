import subprocess,shlex
q=r'''from pathlib import Path
import json,sys
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');s=b/'source-134'
sys.path[:0]=[str(s/'project/experiments/control_v1'),str(s/'project/experiments/block_v1')]
from s_escape_repair import vertical_plan
from native_escape import records,signature,parse
p=b/'s-escape-repair-01/candidate-1330/before.def'
rows=[r for r in records(p)if r.lstrip().split()[1]=='dout[58]'];assert len(rows)==1
text=rows[0];new,plan=vertical_plan(text,(1760190,840140));_,old=parse(text);_,actual=parse(new)
assert signature(actual)==signature(plan['final_paths'])
assert signature([p for p in actual if int(p['layer'][5:])<=9])==signature([p for p in old if int(p['layer'][5:])<=9])
assert signature([p for p in actual if p['via']])==signature([p for p in old if p['via']])
ten=[p for p in actual if p['layer']=='metal10'];assert len(ten)==2
assert ten[0]['points']==[(1760190,840140,0),(1760190,848140,None)]
assert ten[1]['points']==[(1760190,848140,None),(1756990,848140,None)]
assert plan['final_length_dbu']['metal10']==11200
for pin in [(1760191,840140),(1760190,840141)]:
 try:vertical_plan(text,pin)
 except AssertionError:pass
 else:raise AssertionError('Wrong physical pin accepted')
print(json.dumps(dict(passed=True,metadata_only=True,actual_source=str(p),lower_layers_and_vias_preserved=True,other_L_equal_length=True,wrong_pin_rejected=True,native_drc_and_timing_qualified=False)))
'''
print(subprocess.check_output(['ssh','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)]).decode())
