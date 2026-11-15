"""Resource admission for native candidates, before global DP scheduling.

A control owner is not a physical endpoint. Its LC is nevertheless a finite
execution resource. Candidate SRAM reservations persist across CALL completion:
a completed producer CALL does not release data needed by a later consumer.
"""
import struct,zlib
def admit(candidate,hardware):
 groups=hardware['control_groups'];macros=hardware['macro_instances']
 owners=set(candidate['groups']);controllers=[]
 for owner in sorted(owners):
  if owner not in groups or groups[owner].get('hard_boundary') is not False:
   raise ValueError('unknown or physically boxed control owner')
  lc=groups[owner]['controller']
  if lc not in hardware['controllers'] or hardware['controllers'][lc]['control_owner']!=owner:
   raise ValueError('missing actual local controller')
  controllers.append(lc)
 leases=set(candidate['required_macro_leases'])
 for site,reservation in candidate['srams'].items():
  if site not in macros or macros[site]['role']!='S' or macros[site]['control_owner'] not in owners:
   raise ValueError('SRAM reservation is not an owned macro')
  capacity=macros[site]['source_profile']['capacity_bytes']//16
  start,count=reservation['word'],reservation['words']
  if type(start) is not int or type(count) is not int or start<0 or count<=0 or start+count>capacity:
   raise ValueError('candidate SRAM reservation exceeds actual macro capacity')
  leases.add(site)
  # Current candidate schedules use the reservation until their last commit.
  # Narrower interleaving requires explicit data lifetimes, not CALL retirement.
 for name in leases:
  if name not in macros or macros[name]['control_owner'] not in owners:
   raise ValueError('lease does not identify a selected functional macro')
 for name in candidate['required_registered_adapters']:
  if name not in hardware['adapter_instances']:
   raise ValueError('candidate invents an active adapter')
 targets={t['group']:t for t in hardware['native_dispatch_overlay']['targets']}
 for index,call in enumerate(candidate['calls']):
  if call['index']!=index or any(type(j) is not int or not 0<=j<index for j in call['after']):
   raise ValueError('invalid native call dependency')
  owner=call['group']
  if owner not in owners or call['target']!=targets[owner]['id']:
   raise ValueError('CALL target differs from selected owner')
  raw=bytes.fromhex(call['descriptor_hex'])
  if len(raw)!=128 or zlib.crc32(raw[:124])!=int.from_bytes(raw[124:],'little'):
   raise ValueError('native descriptor CRC/length')
  schema,length,op,abi,topology=struct.unpack_from('<IHHII',raw)
  if length!=128 or topology!=hardware['native_dispatch_overlay']['topology_id']:
   raise ValueError('descriptor not bound to this topology')
  if not any((r['schema'],r['abi'],r['opcode'])==(schema,abi,op) for r in targets[owner]['routes']):
   raise ValueError('CALL has no implemented dispatch route')
  site=groups[owner]['private_sram'];windows=[]
  if schema in (0x314c5244,0x31535744):
   first=struct.unpack_from('<H',raw,16)[0]
   address=struct.unpack_from('<Q',raw,24)[0]
   if call['sram_word']!=first or call['byte_count']!=512 or call['ddr_address']!=address:
    raise ValueError('transfer metadata differs from executable descriptor')
   windows=[(first,32)]
  elif schema==0x31444d45:
   windows=[(struct.unpack_from('<H',raw,20)[0],1)]
  elif schema==0x3156534e:
   first,count=struct.unpack_from('<HH',raw,16);windows=[(first,(count+3)//4)]
   if op!=1:windows.append((struct.unpack_from('<H',raw,26)[0],1))
  elif schema==0x3152504d:
   a,out=struct.unpack_from('<HH',raw,84)
   windows=[(struct.unpack_from('<H',raw,120)[0],32),(a,16),(out,raw[74]*2)]
  elif schema==0x32485447:
   size,word=struct.unpack_from('<HH',raw,40);windows=[(word,size//16)]
  elif schema==0x31414d52:
   x,g,count,f=struct.unpack_from('<4H',raw,16);windows=[(x,count),(g,count),(f,1)]
  elif schema==0x31455052:
   windows=[(word,32) for word in struct.unpack_from('<4H',raw,16)]
  elif schema==0x314d5347 or (schema,abi,op)==(3,7,2):
   a,b,out,count=struct.unpack_from('<4H',raw,16);windows=[(a,count),(b,count),(out,count)]
  else:raise ValueError('no SRAM footprint contract for descriptor '+hex(schema))
  if site not in candidate['srams']:raise ValueError('CALL SRAM has no persistent reservation')
  reserved=candidate['srams'][site];lo=reserved['word'];hi=lo+reserved['words']
  if any(count<=0 or first<lo or first+count>hi for first,count in windows):
   raise ValueError('CALL exceeds its candidate SRAM reservation')
  call['resource_requirements']={'controller':groups[owner]['controller'],
   'controller_slots':1,'sram':site,
   'sram_windows':[{'word':first,'words':count} for first,count in windows]}
 candidate['required_macro_leases']=sorted(leases)
 candidate['required_controller_leases']=controllers
 candidate['resource_admission']={
  'checked':True,'scope':'candidate capacity/identity/dispatch only; global schedule and physical wiring pending',
  'controller_capacity':1,'reservation_lifetime':'candidate_start_to_last_output_commit',
  'whole_plan_accepted':False}
 return candidate
