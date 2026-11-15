"""Graph Add through a selected E32 macro and explicit operand transfers."""
import struct,zlib
from native_backend import NativeBackend
from native_p_candidates import _storage,row_transfer
from native_candidate_resources import admit
def candidate(task,*,binding,regions,hardware):
 if task['kind']!='Add' or binding['service_module']!='add_s32_service_controller':
  raise ValueError('Add task and actual Add binding required')
 owner=binding['control_owner'];macro=hardware['macro_instances'][binding['resources']['e']]
 if macro['control_owner']!=owner or macro['master']!='e_s32_mac_ap64':
  raise ValueError('native Add E32 revision/owner')
 backend=NativeBackend(hardware['native_dispatch_overlay']);calls=[]
 def append(c):calls.append(dict(c,index=len(calls),after=[] if not calls else [len(calls)-1]))
 def row(access,offset):
  region=regions[access['root']];_storage(region,access['root'],-16)
  found=[s for s in access['segments'] if s['destination_element']<=offset and offset+128<=s['destination_element']+s['elements']]
  if len(found)!=1:raise ValueError('Add row needs explicit segmented materialization')
  s=found[0];at=s['source_element']+offset-s['destination_element']
  if at<0 or (at+128)*4>region['bytes']:raise ValueError('Add operand extent')
  return region,at*4
 for tile_index,tile in enumerate(task['tiles']):
  write=tile['write'];count=write['elements'];out=regions[write['value']]
  _storage(out,write['value'],-16)
  if not count or count%128 or len(tile['read'])!=2 or any(a['elements']!=count for a in tile['read']):
   raise ValueError('Add row geometry')
  for first in range(0,count,128):
   for access,word in zip(tile['read'],(0,32)):
    source,offset=row(access,first)
    append(row_transfer(backend,owner,source,direction='load',sram_word=word,offset=offset,value=access['value']))
   raw=bytearray(128)
   struct.pack_into('<IHHII4H',raw,0,3,128,2,7,backend.topology,0,32,64,32)
   struct.pack_into('<I',raw,124,zlib.crc32(raw[:124]))
   c=backend.encode_deployment_call(owner,('service_done',lambda _:bytes(raw)),{'required_completion':'service_done'})
   append({'target':c.target,'group':owner,'direction':'compute','operator':'Add','tile':tile_index,
     'descriptor_hex':c.descriptor.hex(),'completion':c.completion})
   append(row_transfer(backend,owner,out,direction='store',sram_word=64,
    offset=(write['element_offset']+first)*4,value=write['value']))
 return admit({'source_task':task['id'],'binding':task['id']+'@E:'+owner,
  'groups':[owner],'calls':calls,'connections':binding['required_connections'],
  'required_macro_leases':binding['required_macro_leases'],
  'required_registered_adapters':binding['required_registered_adapters'],
  'srams':{binding['private_sram']:{'word':0,'words':96}},
  'completion':'last_output_DDR_commit','scope':'native Add candidate; full RTL and global plan acceptance required'},hardware)
