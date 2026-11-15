"""Verify emitted binary control using PR260's interpreter; not timed execution."""
import json,sys
from pathlib import Path
from native_package_runtime import load
from replay_tlm_mother import execute
root=Path(sys.argv[1])
manifest,payloads,pages=load(root)
expected=json.loads(payloads['control-actions.json'])
calls=json.loads(payloads['calls.json'])
observed=[];position=0;live={}
def issue(target,slot,regs):
    global position
    c=calls[position]
    if (target,slot,regs[0]+(regs[1]<<32))!=(c['target'],target,c['address']):
        raise ValueError('binary CALL differs from selected plan')
    if regs[2:7]!=(0x00010080,0x02510001,manifest['topology'],0x02500002,0):
        raise ValueError('binary CALL metadata mismatch')
    observed.append({'op':'CALL','target':target,'call_index':c['source_call']})
    live[target]=c['source_call'];position+=1
    return target
def wait(handles):
    observed.append({'op':'WAIT','mask':sum(1<<t for t in handles),
                     'calls':sorted(live[t] for t in handles)})
    for t in handles:del live[t]
for page in pages:
    execute(page['instructions'],issue=issue,wait=wait,max_steps=page['max_steps'],entry_pc=page['entry_pc'])
    if live:raise ValueError('page transition with live call')
if observed!=expected or position!=len(calls):raise ValueError('binary control trace differs from plan')
report={'passed':True,'pages':len(pages),'calls':position,'actions':len(observed),
        'scope':'PR260 binary interpreter control trace only; no timed providers or RTL execution',
        'delivery_accepted':False}
(root/'binary-control-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
