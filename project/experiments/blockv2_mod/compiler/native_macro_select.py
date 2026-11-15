"""Bounded DP on declared macro/LC/adapter resources, followed by native re-encoding."""
from pathlib import Path
from hashlib import sha256
import gzip,json
from native_macro_work import measure
from loop_dp import search
from verify_loop_dp import verify
def digest(value):return sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def select(frontend,candidate_directory,*,width=8,progress=print):
 directory=Path(candidate_directory);manifest=json.loads((directory/'manifest.json').read_text())
 if manifest['graph_sha256']!=frontend.graph_hash or manifest['storage']!=frontend.storage:
  raise ValueError('candidate graph/storage differs from live frontend')
 if manifest['hardware']!=frontend.hardware:raise ValueError('candidate hardware differs from live frontend')
 base=frontend.hardware
 resources={name:1 for name in base['macro_instances']}
 resources.update({name:1 for name in base['controllers']})
 resources.update({name:meta['capacity'] for name,meta in base['adapter_instances'].items()})
 sites={name:{'words':m['source_profile']['capacity_bytes']//16} for name,m in base['macro_instances'].items() if m['role']=='S'}
 hw={'resources':resources,'sites':sites,'nets':{},'incompatible_nets':[],
     'topology_id':base['native_dispatch_overlay']['topology_id']}
 tasks=[];option_by={};resource_by={};costs={}
 for row in manifest['tasks']:
  if row['kind']=='View':continue
  source=directory/row['candidate_file']
  if sha256(source.read_bytes()).hexdigest()!=row['candidate_sha256']:raise ValueError('candidate stream changed')
  options=frontend.options(frontend.tasks[row['id']]);bs=[]
  with gzip.open(source,'rt') as stream:
   for i,line in enumerate(stream):
    c=json.loads(line);cost=measure(c)
    claimed=sorted(set(c['required_macro_leases']+c['required_controller_leases']+c['required_registered_adapters']))
    scratch={s:w['word']+w['words'] for s,w in c['srams'].items()}
    site=next(iter(scratch))
    b={'id':c['binding'],'site':site,'ticks':cost['work_units'],'resources':claimed,'nets':[],
       'scratch_words':scratch[site],'scratch_by_site':scratch,
       'external_read_words':(cost['descriptor_bytes']+cost['ddr_read_bytes_upper']+15)//16,
       'external_write_words':(cost['ddr_write_bytes']+15)//16}
    bs.append(b);key=(row['id'],c['binding']);option_by[key]=options[i];resource_by[key]=claimed;costs[key]=cost
  if len(bs)!=len(options):raise ValueError('candidate option count changed')
  tasks.append({'id':row['id'],'after':row['after'],'bindings':bs})
 progress('Starting bounded macro/LC DP')
 schedule=search(tasks,hw,width=width,ready_limit=4,wire_lookahead=False)
 if schedule['status']!='planned':raise ValueError('DP did not find a plan: '+str(schedule))
 cold_proof=verify(tasks,hw,schedule)
 if frontend.range_tiles:
  from functools import lru_cache
  from native_resident_binding_search import refine
  files={r['id']:directory/r['candidate_file'] for r in manifest['tasks'] if r['kind']!='View'}
  @lru_cache(maxsize=64)
  def choices(name):
   with gzip.open(files[name],'rt') as stream:return {c['binding']:c for c in map(json.loads,stream)}
  tasks,schedule=refine(tasks,schedule,lambda n,b:choices(n)[b],width=min(width,4))
 proof=verify(tasks,hw,schedule)
 ids=dict(frontend.initial_ids);resident_state={};residency=[];calls=[];selected=[];ends={};resource_ends={};connections={}
 for row in schedule['tasks']:
  key=(row['id'],row['binding']);task=frontend.tasks[row['id']]
  c=frontend.encode(task,option_by[key],ids)
  if c['binding']!=row['binding']:raise ValueError('selected encoding changed binding')
  ids.update(c.get('next_identities',{}))
  if frontend.range_tiles:
   from native_range_residency import rewrite
   c,resident_state=rewrite(c,resident_state)
   residency.append({'task':row['id'],'elisions':c['resident_load_elisions']})
  external=set()
  for parent in frontend.after[row['id']]:external.update(ends[parent])
  for resource in resource_by[key]:external.update(resource_ends.get(resource,()))
  first=len(calls)
  for call in c['calls']:
   copy=dict(call,index=first+call['index'],source_task=row['id'])
   copy['after']=[first+i for i in call['after']] if call['after'] else sorted(external)
   calls.append(copy)
  used={j for call in c['calls'] for j in call['after']}
  terminal={first+i for i in range(len(c['calls'])) if i not in used}
  ends[row['id']]=terminal
  for resource in resource_by[key]:resource_ends[resource]=terminal
  for edge in c.get('connections',[]):connections[digest(edge)]=edge
  selected.append({'source_task':row['id'],'binding':row['binding'],'first_call':first,
   'call_count':len(c['calls']),'resources':resource_by[key],'work_estimate':costs[key]})
 wiring={'connections':list(connections.values()),'physical_binding_complete':False,
  'missing':['complete parent SRAM/DDR/control endpoint registration','endpoint compatibility and physical realization'],
  'scope':'selected compute endpoint requirements only; not a complete wiring solution'}
 result={'schema':'macro-native-selected-plan/1','graph_sha256':frontend.graph_hash,
  'selection':selected,'calls':calls,'storage':frontend.storage,'hardware':base,'wiring':wiring,
  'search_plan':schedule,'search_verification':proof,'search_tasks':tasks,'search_hardware':hw,
  'view_aliases':{n:t['alias'] for n,t in frontend.tasks.items() if t['kind']=='View'},
  'range_tiles':frontend.range_tiles,'range_parts':frontend.range_parts,
  'residency':residency,'residency_search_priced':bool(frontend.range_tiles),
  'delivery_accepted':False,'timing_calibrated':False,
  'timing_scope':'structural work proxy for DP; completion-controlled executable order; TLM timing still required',
  'wire_optimization_performed':False}
 result['plan_sha256']=digest(result)
 progress('Selected '+str(len(selected))+' tasks and '+str(len(calls))+' native calls')
 return result
