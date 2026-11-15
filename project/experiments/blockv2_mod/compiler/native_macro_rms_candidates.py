"""RMSNorm: real N factor, committed DDR transfer, E application; no host factor."""
import math,json
from native_backend import NativeBackend
from native_p_candidates import _storage,row_transfer
from n32_service_descriptor import encode as reduce
from rms_apply_native_descriptor import encode as apply
from native_candidate_resources import admit
def candidate(task,*,n_binding,e_binding,regions,hardware,workspace):
 if task['kind']!='RMSNorm' or n_binding['service_module']!='n32_service_controller' or e_binding['service_module']!='rms_apply_native_service_controller':
  raise ValueError('native RMS bindings required')
 n=n_binding['control_owner'];e=e_binding['control_owner']
 for binding,role,master in [(n_binding,'n','n_s32_mod'),(e_binding,'e','e_s32_mac_ap64')]:
  m=hardware['macro_instances'][binding['resources'][role]]
  if m['master']!=master or m['control_owner']!=binding['control_owner']:raise ValueError('RMS macro binding')
 _storage(workspace,workspace['value'],-16)
 if workspace['bytes']<512 or workspace['base']%512 or any(
  workspace['base']<r['base']+r['bytes'] and r['base']<workspace['base']+workspace['bytes'] for r in regions.values()):
  raise ValueError('RMS factor packet workspace')
 backend=NativeBackend(hardware['native_dispatch_overlay']);calls=[];maxwords=0
 def append(call):calls.append(dict(call,index=len(calls),after=[] if not calls else [len(calls)-1]))
 def invoke(owner,raw,part):
  c=backend.encode_deployment_call(owner,('service_done',lambda _:raw),{'required_completion':'service_done'})
  append({'target':c.target,'group':owner,'direction':'compute','operator':'RMSNorm',
   'recipe_part':part,'descriptor_hex':raw.hex(),'completion':c.completion})
 def load(access,offset,owner,word):
  region=regions[access['root']];_storage(region,access['root'],-16)
  matches=[s for s in access['segments'] if s['destination_element']<=offset and offset+128<=s['destination_element']+s['elements']]
  if len(matches)!=1:raise ValueError('RMS segmented row needs materialization')
  s=matches[0];at=(s['source_element']+offset-s['destination_element'])*4
  append(row_transfer(backend,owner,region,direction='load',sram_word=word,offset=at,value=access['value']))
 for tile in task['tiles']:
  count=tile['reduction_elements'];write=tile['write'];eps=tile['epsilon']
  if not 0<count<=4096 or count%128 or len(tile['read'])!=2 or write['elements']!=count:
   raise ValueError('RMS reduction geometry')
  if any(a['elements']!=count for a in tile['read']):raise ValueError('RMS operand geometry')
  if not math.isfinite(eps) or eps<=0:raise ValueError('RMS epsilon')
  epsilon=round(eps*(1<<32))
  if not 0<epsilon<2**32:raise ValueError('RMS epsilon precision')
  x,g=tile['read'];maxwords=max(maxwords,count//4)
  for first in range(0,count,128):load(x,first,n,first//4)
  # The scalar replaces source word zero only after reduction has consumed all inputs.
  invoke(n,reduce(operation='RMSFactor',topology=backend.topology,source_word=0,
   elements=count,result_word=0,epsilon_mantissa=epsilon,epsilon_shift=0,baseline_shift=0),'factor')
  append(row_transfer(backend,n,workspace,direction='store',sram_word=0,offset=0,value=workspace['value']))
  append(row_transfer(backend,e,workspace,direction='load',sram_word=64,offset=0,value=workspace['value']))
  out=regions[write['value']];_storage(out,write['value'],-16)
  for first in range(0,count,128):
   load(x,first,e,0);load(g,first,e,32)
   invoke(e,apply(topology=backend.topology,x_word=0,gamma_word=32,words=32,factor_word=64),'apply')
   append(row_transfer(backend,e,out,direction='store',sram_word=0,
    offset=(write['element_offset']+first)*4,value=write['value']))
 connections=list({json.dumps(c,sort_keys=True):c for c in n_binding['required_connections']+e_binding['required_connections']}.values())
 return admit({'source_task':task['id'],'binding':task['id']+'@N:'+n+'@E:'+e,
  'groups':[n,e],'calls':calls,'connections':connections,
  'required_macro_leases':sorted(set(n_binding['required_macro_leases']+e_binding['required_macro_leases'])),
  'required_registered_adapters':sorted(set(n_binding['required_registered_adapters']+e_binding['required_registered_adapters'])),
  'srams':{n_binding['private_sram']:{'word':0,'words':maxwords},
           e_binding['private_sram']:{'word':0,'words':96}},
  'workspace':workspace,'completion':'last_output_DDR_commit',
  'scope':'native graph RMS candidate; full N-to-E execution and global plan still require acceptance'},hardware)
