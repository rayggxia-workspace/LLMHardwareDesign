"""Exact committed DDR-backed residency on existing 16-byte SRAM words.

Only redundant DRL1 calls are removed. Stores/commit points are preserved.
Unknown service write footprints invalidate the entire selected SRAM.
No dirty value is silently evicted; no new route or copy operation is assumed.
"""
import struct
from copy import deepcopy

def rewrite(candidate,state):
 state={g:dict(words) for g,words in state.items()}
 calls=[];terminals={};removed=[]
 for old,call in enumerate(candidate['calls']):
  if call['index']!=old or any(i>=old for i in call['after']):raise ValueError('unordered candidate calls')
  # Candidates are sequential within an LC; state changes are committed.
  if old and call['after']!=[old-1]:raise ValueError('residency requires a committed sequential candidate')
  raw=bytes.fromhex(call['descriptor_hex']);schema=int.from_bytes(raw[:4],'little')
  owner=call['group'];words=state.setdefault(owner,{})
  skip=False
  if schema in (0x314c5244,0x31535744):
   word=struct.unpack_from('<H',raw,16)[0];address=struct.unpack_from('<Q',raw,24)[0]
   if word+32>1024 or address%64:raise ValueError('DMA residency extent')
   if schema==0x314c5244:
    skip=all(words.get(word+i)==address+16*i for i in range(32))
    for i in range(32):words[word+i]=address+16*i
   else:
    # A newly committed write supersedes every old cached version of this span.
    for cached in state.values():
     for w,a in list(cached.items()):
      if address<=a<address+512:del cached[w]
    for i in range(32):words[word+i]=address+16*i
  else:
   span=None
   if schema in (3,0x314d5347):
    dst,n=struct.unpack_from('<HH',raw,20);span=(dst,n)
   elif schema==0x31455052:span=(struct.unpack_from('<H',raw,22)[0],32)
   elif schema==0x31414d52:
    x,g,n,f=struct.unpack_from('<4H',raw,16);span=(x,n)
   elif schema==0x3156534e:
    op=int.from_bytes(raw[6:8],'little');base,n=struct.unpack_from('<HH',raw,16)
    span=(base,(n+3)//4) if op==1 else (struct.unpack_from('<H',raw,26)[0],1)
   elif schema==0x31444d45:span=(struct.unpack_from('<H',raw,20)[0],1)
   elif schema==0x32485447:
    n,dst=struct.unpack_from('<HH',raw,40);span=(dst,n//16)
   if span is None:words.clear()
   else:
    for w in range(span[0],span[0]+span[1]):words.pop(w,None)
  predecessors=sorted({j for p in call['after'] for j in terminals[p]})
  if skip:
   removed.append({'original_call':old,'group':owner,'sram_word':word,'ddr_address':address,'bytes':512})
   terminals[old]=predecessors
  else:
   copy=dict(call,index=len(calls),after=predecessors);calls.append(copy);terminals[old]=[copy['index']]
 result={**candidate,'calls':calls,'resident_load_elisions':removed}
 return result,state
