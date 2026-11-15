"""Accept only complete, bit-exact executions with identical input/base/timing models."""
import argparse,json,hashlib,ast
from collections import Counter
from pathlib import Path
from native_package_runtime import load
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def inputs(asset):
 return {k:v for k,v in asset.items() if k not in ('plan_sha256','rebound_from_plan_sha256','input_reuse_proof')}
def timing_sources(receipt):
 return {k:v for k,v in receipt['source_sha256'].items()
         if Path(k).name.startswith('macro_') or Path(k).name=='reference.py'}
def main():
 p=argparse.ArgumentParser();p.add_argument('spec',type=Path);p.add_argument('output',type=Path);a=p.parse_args()
 spec=read(a.spec);rows=[];errors=[];anchor=None
 for item in spec['variants']:
  try:
   rec=read(item['execution']);cmp=read(item['comparison']);assets=read(item['assets'])
   manifest,payloads,_=load(item['package'])
   if rec['status']!='all_instructions_executed' or rec['completed_calls']!=manifest['native_calls']:
    raise ValueError('not all instructions executed')
   if rec['plan_sha256']!=manifest['plan_sha256'] or cmp['plan_sha256']!=rec['plan_sha256']:
    raise ValueError('plan binding mismatch')
   if rec['asset_manifest_sha256']!=digest(item['assets']):raise ValueError('asset manifest seal mismatch')
   if cmp['execution_receipt_sha256']!=digest(item['execution']):raise ValueError('comparison receipt seal mismatch')
   if not (cmp.get('all_exported_values_bit_exact') or cmp.get('all_produced_tensors_bit_exact')):
    raise ValueError('numeric comparison failed')
   basis={'graph':manifest['graph_sha256'],'hardware':payloads['hardware.json'],
    'storage':payloads['storage.json'],'inputs':inputs(assets),'timing_models':timing_sources(rec),
    **{k:rec[k] for k in ('core_ps','dram_library_sha256','dram_config_sha256','sram_config_sha256')}}
   if anchor is None:anchor=basis
   elif basis!=anchor:
    raise ValueError('comparison inputs differ: '+','.join(k for k in basis if basis[k]!=anchor[k]))
   ddr=(rec['DDR']['reads']+rec['DDR']['writes'])*64
   targets={t['id']:t['group'] for t in json.loads(payloads['hardware.json'])['native_dispatch_overlay']['targets']}
   occupied=Counter()
   for key,value in rec['service_elapsed_ps'].items():occupied[targets[ast.literal_eval(key)[0]]]+=value
   rows.append({'name':item['name'],'plan_sha256':rec['plan_sha256'],'calls':rec['completed_calls'],
    'time_ps':rec['time_ps'],'DDR_total_bytes':ddr,'DDR_read_bytes':rec['DDR']['reads']*64,
    'DDR_write_bytes':rec['DDR']['writes']*64,'transport_queue_wait_ps_sum':rec['transport'].get('queue_wait_ps',0),
    'SRAM':rec['SRAM'],'LC_reserved_fraction_including_memory_waits':{k:v/rec['time_ps'] for k,v in occupied.items()},'numeric_accepted':True,'execution_receipt_sha256':digest(item['execution'])})
  except Exception as e:errors.append({'name':item['name'],'error':str(e)})
 if rows:
  base=rows[0]
  for r in rows:
   r['time_change_vs_first']=r['time_ps']/base['time_ps']-1
   r['DDR_change_vs_first']=r['DDR_total_bytes']/base['DDR_total_bytes']-1
   r['dominated_by']=[q['name'] for q in rows if q is not r and
    q['time_ps']<=r['time_ps'] and q['DDR_total_bytes']<=r['DDR_total_bytes'] and
    (q['time_ps']<r['time_ps'] or q['DDR_total_bytes']<r['DDR_total_bytes'])]
 result={'schema':'same-input-decode-variant-comparison/1','variants':rows,'invalid':errors,
  'all_requested_variants_accepted':not errors and bool(rows),
  'fastest_verified_model_execution':min(rows,key=lambda r:(r['time_ps'],r['DDR_total_bytes']))['name'] if rows else None,
  'scope':'one full decode, archived real history length two; modeled time, not calibrated physical throughput',
  'warning':'queue waits summed across clients overlap and are not critical-path time',
  'source_sha256':digest(__file__)}
 a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
 if errors:raise SystemExit(1)
if __name__=='__main__':main()
