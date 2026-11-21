"""Conditional prefill throughput; explicitly no decode or calibrated energy."""
import argparse,hashlib,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--frequency-mhz',type=float,required=True)
p.add_argument('--prefill-tokens',type=int,required=True);a=p.parse_args()
if a.frequency_mhz<=0 or a.prefill_tokens<1:raise ValueError('positive explicit assumptions required')
root=Path(__file__).resolve().parent
source=json.loads((root/'generated/input-report.json').read_text())
matches=re.findall(r'^\{.*\}$',(root/'replay.log').read_text(),re.MULTILINE)
if len(matches)!=1:raise ValueError('one SystemC result required')
sim=json.loads(matches[0])
if sim['completed']!=source['execution_units']:raise ValueError('incomplete SystemC replay')
if sim['model_ticks']!=source['dependency_resource_order_ticks']:raise ValueError('SystemC and independent Python event DAG disagree')
seconds=sim['model_ticks']/(a.frequency_mhz*1e6)
result={'status':'exploratory_uncalibrated','kind':'SystemC compiled-service resource-order timing replay',
 'scope':'Qwen2.5-3B B1/S2 prefill, 36 layers including embedding and LM head; no KV/decode; host/tokenization/sampling excluded',
 'systemc':sim,'native_schedule_evidence':source,'assumptions':{'core_frequency_mhz':a.frequency_mhz,
 'one_model_tick_per_core_cycle':True,'prefill_tokens':a.prefill_tokens,
 'memory':'same frozen PR182 bounded virtual model; not measured DRAM'},
 'conditional_prefill_seconds':seconds,'conditional_prefill_tokens_per_second':a.prefill_tokens/seconds,
 'decode_tokens_per_second':None,'energy_joules':None,
 'nominal_descriptor_bytes':source['logical_128bit_records']*16,
 'nominal_descriptor_bytes_per_second':source['logical_128bit_records']*16/seconds,
 'qualification':'Independent SystemC event execution validates this service-order replay only. Durations inherited from compiler; does not calibrate macro/MC/LC/DRAM timing or predict optimal hardware throughput.',
 'sha256':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in ('replay.cpp','prepare.py','run.sbatch','report.py','generated/tasks.txt','generated/input-report.json','replay.log')}}
(root/'report.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:result[k] for k in ('status','conditional_prefill_seconds','conditional_prefill_tokens_per_second','decode_tokens_per_second','nominal_descriptor_bytes')}))
