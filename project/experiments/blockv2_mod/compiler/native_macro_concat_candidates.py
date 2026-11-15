"""Concat materializes rows using the selected owner's implemented load/store path."""
from native_backend import NativeBackend
from native_p_candidates import _storage,row_transfer
from native_candidate_resources import admit
def candidate(task,*,owner,regions,hardware):
 if task['kind']!='Concat' or owner not in hardware['control_groups']:
  raise ValueError('Concat and declared controller required')
 group=hardware['control_groups'][owner];site=group['private_sram']
 macro=hardware['macro_instances'][site]
 if macro['role']!='S' or macro['control_owner']!=owner:raise ValueError('Concat SRAM owner')
 backend=NativeBackend(hardware['native_dispatch_overlay']);calls=[];writes={}
 def append(c):calls.append(dict(c,index=len(calls),after=[] if not calls else [len(calls)-1]))
 for tile in task['tiles']:
  if len(tile['read'])!=1:raise ValueError('Concat tile source')
  access,=tile['read'];write=tile['write'];src=regions[access['root']];dst=regions[write['value']]
  _storage(src,access['root'],-16);_storage(dst,write['value'],-16)
  if src['base']<dst['base']+dst['bytes'] and dst['base']<src['base']+src['bytes']:
   raise ValueError('overlapping Concat storage requires a separate move plan')
  count=write['elements'];start=write['element_offset']
  if count<=0 or count%128 or start<0 or start%128 or access['elements']!=count or (start+count)*4>dst['bytes']:
   raise ValueError('Concat output row extent')
  writes.setdefault(write['value'],[]).append((start,start+count))
  covered=0
  for segment in access['segments']:
   source=segment['source_element'];dest=segment['destination_element'];length=segment['elements']
   if dest!=covered or source<0 or source%128 or length<=0 or length%128 or (source+length)*4>src['bytes']:
    raise ValueError('Concat source coverage/alignment')
   for first in range(0,length,128):
    append(row_transfer(backend,owner,src,direction='load',sram_word=0,offset=(source+first)*4,value=access['value']))
    append(row_transfer(backend,owner,dst,direction='store',sram_word=0,offset=(start+dest+first)*4,value=write['value']))
   covered+=length
  if covered!=count:raise ValueError('Concat source does not cover output')
 for value,intervals in writes.items():
  end=0
  for lo,hi in sorted(intervals):
   if lo!=end:raise ValueError('Concat output gap or duplicate write')
   end=hi
  if end*4!=regions[value]['bytes']:raise ValueError('Concat output incomplete')
 return admit({'source_task':task['id'],'binding':task['id']+'@transfer:'+owner,
  'groups':[owner],'calls':calls,'connections':[],
  'required_macro_leases':[site],'required_registered_adapters':[],
  'srams':{site:{'word':0,'words':32}},'completion':'last_destination_DDR_commit',
  'scope':'native transfer candidate; SRAM/DDR endpoint binding and global schedule pending',
  'unresolved_connection_requirements':['selected parent SRAM path','shared DDR client binding']},hardware)
