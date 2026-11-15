"""Runtime embedding Gather using the implemented indexed DMA service."""
from native_backend import NativeBackend
from native_p_candidates import _storage,row_transfer
from native_candidate_resources import admit
from indexed_gather_descriptor import encode
def candidate(task,*,owner,regions,hardware):
 if task['kind']!='Gather':raise ValueError('Gather task required')
 backend=NativeBackend(hardware['native_dispatch_overlay'])
 site=hardware['control_groups'][owner]['private_sram'];calls=[];constraints=[]
 def append(c):calls.append(dict(c,index=len(calls),after=[] if not calls else [len(calls)-1]))
 for tile_index,tile in enumerate(task['tiles']):
  table=regions[tile['indexed_table']];_storage(table,tile['indexed_table'],-16)
  rows=tile['table_rows'];write=tile['write'];row_bytes=write['elements']*4
  if row_bytes<512 or row_bytes&(row_bytes-1) or table['bytes']!=rows*row_bytes:
   raise ValueError('Gather table row layout')
  shift=row_bytes.bit_length()-1
  access,=tile['read'];indices=regions[access['root']];width=indices['element_bytes']
  if width not in (4,8) or indices.get('encoding')!='signed-int'+str(width*8)+'-exact':
   raise ValueError('Gather requires exact runtime signed index storage')
  if access['elements']!=1 or len(access['segments'])!=1:raise ValueError('Gather index view')
  segment,=access['segments']
  if segment['elements']!=1 or segment['destination_element']!=0:raise ValueError('Gather scalar index')
  offset=segment['source_element']*width
  if offset<0 or offset+width>indices['bytes']:raise ValueError('Gather index extent')
  index_address=indices['base']+offset
  out=regions[write['value']];_storage(out,write['value'],-16)
  for first in range(0,row_bytes,512):
   raw=encode(topology=backend.topology,table_address=table['base'],index_address=index_address,
    rows=rows,row_shift=shift,index_bytes=width,offset=first,byte_count=512,sram_word=0)
   c=backend.encode_deployment_call(owner,('service_done',lambda _:raw),{'required_completion':'service_done'})
   append({'target':c.target,'group':owner,'direction':'gather','tile':tile_index,
    'descriptor_hex':c.descriptor.hex(),'completion':c.completion,
    'runtime_index_address':index_address,'runtime_index_bytes':width})
   append(row_transfer(backend,owner,out,direction='store',sram_word=0,
    offset=write['element_offset']*4+first,value=write['value']))
  constraints.append({'value':access['root'],'source_dtype':tile['index_dtype'],
   'native_encoding':indices['encoding'],'index_bytes':width,
   'conversion':'input materializer must reject nonrepresentable indices; no truncation',
   'hardware_range_check':{'minimum':-rows,'maximum':rows-1}})
 return admit({'source_task':task['id'],'binding':task['id']+'@indexed:'+owner,
  'groups':[owner],'calls':calls,'connections':[],
  'required_macro_leases':[site],'required_registered_adapters':[],
  'srams':{site:{'word':0,'words':32}},'runtime_input_constraints':constraints,
  'completion':'last_output_DDR_commit',
  'unresolved_connection_requirements':['selected parent SRAM path','shared DDR client binding'],
  'scope':'native runtime-index candidate; global plan and endpoint wiring pending'},hardware)
