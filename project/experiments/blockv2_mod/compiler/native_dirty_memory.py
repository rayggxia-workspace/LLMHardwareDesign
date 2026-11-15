"""Native 512B page placement, dirty handoff and explicit committed spills.

All rewrites use existing descriptors. No arithmetic or data copies run on host.
Unknown/compound services use their canonical SRAM footprint after dirty flush.
"""
import struct,zlib
from copy import deepcopy

LOAD=0x314c5244
STORE=0x31535744
MPR=0x3152504d
POINT={3:(16,18,20),0x314d5347:(16,18,20),0x31455052:(16,18,20,22)}

def patched(call,fields):
 raw=bytearray.fromhex(call['descriptor_hex'])
 for offset,value in fields.items():struct.pack_into('<H',raw,offset,value)
 struct.pack_into('<I',raw,124,zlib.crc32(raw[:124]))
 result={**call,'descriptor_hex':raw.hex()}
 if int.from_bytes(raw[:4],'little') in (LOAD,STORE):result['sram_word']=struct.unpack_from('<H',raw,16)[0]
 return result

def transform(candidate,state,*,keep,produced,users,done,exports):
 """State is committed at the end of the action, not at issue time."""
 memory={owner:{word:dict(v) for word,v in pages.items()} for owner,pages in state['memory'].items()}
 backed=state['backed'];copies=dict(state.get('copies',{}));emitted=[];events=[];logical={};protected={}
 workspace=candidate.get('_workspace')
 def in_workspace(address):return workspace is not None and workspace['base']<=address<workspace['base']+workspace['bytes']
 capacities=candidate.get('_capacity_words',{})
 def capacity(owner):return capacities.get(owner,1024)
 def emit(call):
  emitted.append(dict(call,index=len(emitted),after=[] if not emitted else [len(emitted)-1]))
 def flush(owner,word):
  nonlocal backed
  page=memory[owner][word]
  if page['dirty']:
   emit(patched(page['store'],{16:word}));page['dirty']=False
   backed|=1<<produced[page['address']]
   events.append({'op':'spill','owner':owner,'word':word,'address':page['address'],'bytes':512})
 def resident(address,owner=None):
  for site,pages in memory.items():
   if owner is not None and site!=owner:continue
   for word,page in pages.items():
    if page.get('address')==address:return site,word
  return None
 def require(address):
  index=produced.get(address)
  if index is None or backed>>index&1:return
  location=resident(address)
  if location is None:raise ValueError('native dirty value has no backing or resident copy '+hex(address))
  flush(*location)
 def invalidate(owner,words):
  pages=memory.setdefault(owner,{})
  for word in list(pages):
   if any(word<=w<word+32 for w in words):
    flush(owner,word);del pages[word]
 def allocate(owner,forbidden=()):
  pages=memory.setdefault(owner,{})
  blocked=set(forbidden)|protected.setdefault(owner,set())
  for word in range(0,capacity(owner)-31,32):
   if word not in pages and not any(word<=w<word+32 for w in blocked):return word
  for dirty in (False,True):
   for word,page in sorted(pages.items()):
    if page['dirty']==dirty and not any(word<=w<word+32 for w in blocked):
     flush(owner,word);del pages[word];return word
  raise ValueError('native SRAM placement exhausted')
 def map_word(owner,word):
  try:return logical[(owner,word)]
  except KeyError:raise ValueError('unbound SRAM operand in relocatable service')
 def register(owner,word,address,dirty=False,store=None):
  memory.setdefault(owner,{})[word]={'address':address,'dirty':dirty,'store':store}
 # Only atomic implemented service families have a relocation contract.
 schemas=[int.from_bytes(bytes.fromhex(c['descriptor_hex'])[:4],'little') for c in candidate['calls']]
 relocatable=any(s in (MPR,*POINT) for s in schemas) and all(s in (LOAD,STORE,MPR,*POINT) for s in schemas)
 if not relocatable:
  # Preserve canonical SRAM behavior and route. Materialize required dirty inputs.
  for address in candidate['_input_pages']:require(address)
  for owner in candidate['groups']:
   invalidate(owner,range(capacity(owner)))
  for call in candidate['calls']:
   emit(call)
   raw=bytes.fromhex(call['descriptor_hex'])
   if int.from_bytes(raw[:4],'little')==STORE:
    address=struct.unpack_from('<Q',raw,24)[0]
    copies.pop(address,None)
    if address in produced:backed|=1<<produced[address]
  return {**candidate,'calls':emitted}, {'memory':memory,'backed':backed,'copies':copies},events
 skip=set()
 for index,call in enumerate(candidate['calls']):
  if index in skip:continue
  if MPR in schemas and workspace is not None and index+1<len(candidate['calls']) and schemas[index:index+2]==[LOAD,STORE]:
   a,b=call,candidate['calls'][index+1]
   ar,br=bytes.fromhex(a['descriptor_hex']),bytes.fromhex(b['descriptor_hex'])
   source=struct.unpack_from('<Q',ar,24)[0];destination=struct.unpack_from('<Q',br,24)[0]
   if a['group']==b['group'] and ar[16:18]==br[16:18] and in_workspace(destination) and not in_workspace(source) and copies.get(destination)==source:
    skip.add(index+1);events.append({'op':'reuse_packed_DDR','address':destination,'source':source,'bytes':512});continue
  raw=bytes.fromhex(call['descriptor_hex']);schema=int.from_bytes(raw[:4],'little');owner=call['group']
  if schema==LOAD:
   original=struct.unpack_from('<H',raw,16)[0];address=struct.unpack_from('<Q',raw,24)[0]
   location=resident(address,owner)
   if location and location[1] in protected.get(owner,set()):location=None
   if location:
    word=location[1];events.append({'op':'local_read','owner':owner,'word':word,'address':address,'bytes':512})
   else:
    require(address);word=allocate(owner);emit(patched(call,{16:word}));register(owner,word,address)
   logical[(owner,original)]=word;protected.setdefault(owner,set()).update(range(word,word+32))
  elif schema==MPR:
   # MPR1 source is DDR; source staging and quantized tile addresses stay literal.
   source_address=struct.unpack_from('<Q',raw,112)[0]
   # The descriptor source is authoritative; packed workspaces already committed.
   source_bytes=struct.unpack_from('<H',raw,76)[0]*4
   for address in range(source_address//512*512,((source_address+source_bytes+511)//512)*512,512):
    if in_workspace(address) and address not in copies:raise ValueError('uncommitted packing workspace')
    require(address)
   source_word=struct.unpack_from('<H',raw,120)[0];a_word=struct.unpack_from('<H',raw,84)[0]
   scratch=set(range(source_word,source_word+32))|set(range(a_word,a_word+16))
   invalidate(owner,scratch)
   output=allocate(owner,scratch);original=struct.unpack_from('<H',raw,86)[0]
   emit(patched(call,{86:output}));logical[(owner,original)]=output
   register(owner,output,None);protected.setdefault(owner,set()).update(range(output,output+32))
  elif schema in POINT:
   offsets=POINT[schema];inputs=[struct.unpack_from('<H',raw,o)[0] for o in offsets[:-1]]
   output=allocate(owner);fields={o:map_word(owner,w) for o,w in zip(offsets[:-1],inputs)}
   fields[offsets[-1]]=output;original=struct.unpack_from('<H',raw,offsets[-1])[0]
   emit(patched(call,fields));logical[(owner,original)]=output;register(owner,output,None)
   protected.setdefault(owner,set()).update(range(output,output+32))
  elif schema==STORE:
   original=struct.unpack_from('<H',raw,16)[0];address=struct.unpack_from('<Q',raw,24)[0]
   word=map_word(owner,original);store=patched(call,{16:word})
   source_identity=memory[owner][word]['address']
   # Only graph SSA outputs may remain unpublished to DDR. Internal scratch commits stay explicit.
   defer=keep and address in produced and address not in exports
   if address in produced or memory[owner][word]['address'] is None:
    register(owner,word,address,defer,store)
   # A pure copy into packing DDR does not rename or destroy its SRAM source.
   if defer:events.append({'op':'retain_dirty','owner':owner,'word':word,'address':address,'bytes':512})
   else:
    emit(store)
    if in_workspace(address):
     if source_identity is None or in_workspace(source_identity):copies.pop(address,None)
     else:copies[address]=source_identity
    if address in produced:backed|=1<<produced[address]
   protected[owner]=set()
 # Last-reader release: never write a dead, non-exported dirty intermediate.
 for owner,pages in memory.items():
  for word,page in list(pages.items()):
   address=page['address']
   if address in produced and address not in exports and not (users.get(address,0)&~done):
    events.append({'op':'release','owner':owner,'word':word,'address':address,'dirty':page['dirty']})
    del pages[word]
 result={**candidate,'calls':emitted}
 return result,{'memory':memory,'backed':backed,'copies':copies},events
