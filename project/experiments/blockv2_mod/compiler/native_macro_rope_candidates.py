"""RoPE native row commands with explicit selected E macro and DDR transfers."""
from native_backend import NativeBackend
from native_p_candidates import _storage,_row_source,row_transfer
from native_rope_descriptor import rope_provider
from native_candidate_resources import admit
def candidate(task,*,binding,regions,hardware):
 if task['kind']!='RoPE' or binding['service_module']!='rope_native_service_controller':
  raise ValueError('native RoPE binding required')
 owner=binding['control_owner'];m=hardware['macro_instances'][binding['resources']['e']]
 if m['master']!='e_s32_mac_ap64' or m['control_owner']!=owner:raise ValueError('RoPE E ownership')
 backend=NativeBackend(hardware['native_dispatch_overlay']);site=binding['private_sram'];calls=[]
 def append(c):calls.append(dict(c,index=len(calls),after=[] if not calls else [len(calls)-1]))
 for index,tile in enumerate(task['tiles']):
  if len(tile['read'])!=3 or tile['elements']!=128 or tile['rotation']!='half-split':
   raise ValueError('RoPE row geometry')
  write=tile['write'];out=regions[write['value']];_storage(out,write['value'],-16)
  if write['elements']!=128:raise ValueError('RoPE output extent')
  names=[a['value'] for a in tile['read']]
  for access,word,exponent in zip(tile['read'],(0,32,64),(-16,-14,-14)):
   region,offset=_row_source(access,regions,exponent)
   append(row_transfer(backend,owner,region,direction='load',sram_word=word,offset=offset,value=access['value']))
  provider=rope_provider(topology=backend.topology,site=site,operands=names,result=write['value'],
   shifts=(14,0,0,14,0,0),source_exponent=-16,native_exponent=-16,output_exponent=-16)
  command={'op':'EXEC','required_completion':'service_done',
   'read':[{'value':v,'site':site,'address':word*16,'bytes':512} for v,word in zip(names,(0,32,64))],
   'write':[{'value':write['value'],'site':site,'address':1536,'bytes':512}]}
  c=backend.encode_deployment_call(owner,provider,command)
  append({'target':c.target,'group':owner,'direction':'compute','operator':'RoPE','tile':index,
   'descriptor_hex':c.descriptor.hex(),'completion':c.completion})
  append(row_transfer(backend,owner,out,direction='store',sram_word=96,
   offset=write['element_offset']*4,value=write['value']))
 return admit({'source_task':task['id'],'binding':task['id']+'@E:'+owner,'groups':[owner],
  'calls':calls,'connections':binding['required_connections'],
  'required_macro_leases':binding['required_macro_leases'],
  'required_registered_adapters':binding['required_registered_adapters'],
  'srams':{site:{'word':0,'words':128}},'completion':'last_output_DDR_commit',
  'scope':'native RoPE candidate; global plan and physical binding pending'},hardware)
