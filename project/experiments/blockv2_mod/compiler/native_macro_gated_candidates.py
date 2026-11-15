"""GSM1 commit units using the existing G macro and its registered controller."""
import struct,zlib
from native_backend import NativeBackend
from native_p_candidates import row_transfer
from native_candidate_resources import admit
def candidate(task,*,binding,regions,hardware):
 owner=binding['control_owner'];backend=NativeBackend(hardware['native_dispatch_overlay']);calls=[]
 def append(c):calls.append(dict(c,index=len(calls),after=[] if not calls else [len(calls)-1]))
 for tile in task['tiles']:
  if tile['write']['elements']!=128:raise ValueError('GSM1 tile geometry')
  for access,word in zip(tile['read'],(0,32)):
   segments=access['segments']
   if len(segments)!=1 or segments[0]['elements']!=128:raise ValueError('GSM1 source geometry')
   append(row_transfer(backend,owner,regions[access['root']],direction='load',sram_word=word,
    offset=segments[0]['source_element']*4,value=access['value']))
  raw=bytearray(128);struct.pack_into('<IHHII4H',raw,0,0x314d5347,128,1,0x02500002,backend.topology,0,32,64,32)
  struct.pack_into('<I',raw,124,zlib.crc32(raw[:124]))
  c=backend.encode_deployment_call(owner,('service_done',lambda _:bytes(raw)),{'required_completion':'service_done'})
  append({'target':c.target,'group':owner,'direction':'gated_compute','descriptor_hex':c.descriptor.hex(),'completion':c.completion})
  w=tile['write'];append(row_transfer(backend,owner,regions[w['value']],direction='store',sram_word=64,
   offset=w['element_offset']*4,value=w['value']))
 return admit({'source_task':task['id'],'binding':task['id']+'@G:'+owner,'groups':[owner],'calls':calls,
  'connections':binding['required_connections'],'required_macro_leases':binding['required_macro_leases'],
  'required_registered_adapters':binding['required_registered_adapters'],
  'srams':{binding['private_sram']:{'word':0,'words':96}},'completion':'last_output_DDR_commit'},hardware)
