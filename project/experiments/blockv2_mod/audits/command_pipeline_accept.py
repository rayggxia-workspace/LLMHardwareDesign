"""Fail closed on wrong history, disconnected steps or incomplete/nonnumeric runs."""
import json,sys,hashlib
from pathlib import Path
def read(p):return json.loads(p.read_text())
root=Path(sys.argv[1]);receipts=[];assets=[]
for h in (512,513):
 r=read(root/f'{h}-execution/receipt.json');a=read(root/f'{h}-assets/assets.json');c=read(root/f'{h}-bit-exact.json')
 if r['status']!='all_instructions_executed' or r['completed_calls']!=r['native_calls']:raise ValueError('incomplete execution')
 if not c['all_exported_values_bit_exact'] or len(c['values_checked'])!=73:raise ValueError('numeric liveout failure')
 if r['plan_sha256']!=a['plan_sha256'] or c['plan_sha256']!=r['plan_sha256']:raise ValueError('plan mismatch')
 if c['execution_receipt_sha256']!=hashlib.sha256((root/f'{h}-execution/receipt.json').read_bytes()).hexdigest():raise ValueError('numeric receipt seal')
 receipts.append(r);assets.append(a)
past=[r for r in assets[0]['regions'] if r['name'].startswith('past_')]
if len(past)!=72 or any(not r['origin'].get('standard_quick_frozen_zero_KV') or r['origin'].get('history_positions')!=512 for r in past):raise ValueError('not frozen history512')
for row in past:
 path=root/'512-assets'/row['file']
 if hashlib.sha256(path.read_bytes()).hexdigest()!=row['sha256']:raise ValueError('initial KV seal changed')
 with path.open('rb') as stream:
  while True:
   block=stream.read(65536)
   if not block:break
   if any(block):raise ValueError('initial historical KV is not frozen zero')
first=next(r for r in assets[0]['regions'] if r['name']=='input_ids')
if first['origin'].get('token')!=840 or int.from_bytes((root/'512-assets'/first['file']).read_bytes()[:4],'little',signed=True)!=840:raise ValueError('wrong first token')
if assets[1].get('source_state_sha256')!=receipts[0]['committed_state']['sha256']:raise ValueError('step2 disconnected from step1')
second=next(r for r in assets[1]['regions'] if r['name']=='input_ids')
logits=next(r for r in receipts[0]['outputs'] if r['value']=='logits')
if second['origin'].get('source_logits_sha256')!=logits['sha256']:raise ValueError('step2 token disconnected')
for key in ('core_ps','dram_config_sha256','dram_library_sha256','sram_config_sha256','source_sha256'):
 if receipts[0][key]!=receipts[1][key]:raise ValueError('timing model changed between steps')
t=[r['time_ps'] for r in receipts]
result={'scenario':'history512/two-causally-chained-decode-steps','numeric_accepted':True,'initial_KV':'frozen_zero','step_times_ps':t,'cumulative_model_retirements_ps':[t[0],sum(t)],'timing_calibrated':False,'transition_loading_time_included':False,'scope':'separate sealed phase executions with actual committed KV/token feedback; external phase installation/relocation excluded, not full hardware request throughput'}
(root/'two-step-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
