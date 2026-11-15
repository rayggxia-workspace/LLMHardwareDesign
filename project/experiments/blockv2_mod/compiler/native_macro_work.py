"""Explicit structural ranking proxy, not time, bandwidth simulation or throughput.

Counts approximate serialized work for comparing candidate schedules. Runtime
ordering uses completion signals, never these estimates. Unknown wire lengths
and unmodeled DDR contention are not treated as validated zero-cost hardware.
"""
import struct
def measure(candidate):
 totals={'descriptor_bytes':0,'ddr_read_bytes_upper':0,'ddr_write_bytes':0,
         'sram_words':0,'arithmetic_elements':0};ends=[]
 for call in candidate['calls']:
  raw=bytes.fromhex(call['descriptor_hex']);schema=int.from_bytes(raw[:4],'little')
  read=write=sram=ops=0;totals['descriptor_bytes']+=128
  if schema==0x314c5244:read=512;sram=32
  elif schema==0x31535744:write=512;sram=32
  elif schema==0x32485447:
   size=struct.unpack_from('<H',raw,40)[0];read=64+size;sram=size//16
  elif schema==3:
   n=struct.unpack_from('<H',raw,22)[0];sram=3*n;ops=4*n
  elif schema==0x31455052:sram=160;ops=128*4
  elif schema==0x31414d52:
   n=struct.unpack_from('<H',raw,20)[0];sram=3*n+1;ops=8*n
  elif schema==0x3156534e:
   n=struct.unpack_from('<H',raw,18)[0];op=struct.unpack_from('<H',raw,6)[0]
   words=(n+3)//4
   sram=4*words if op==1 else 2*words+1 if op==2 else words+1
   ops=n*4 if op==1 else n*2 if op==2 else n
  elif schema==0x31444d45:
   k=struct.unpack_from('<H',raw,16)[0];columns=raw[18]
   # Every requested scalar can miss the one-line service cache.
   read=64*k*(1+columns);sram=1;ops=k*columns+(columns if raw[52] else 0)
  elif schema==0x314d5347:
   n=struct.unpack_from('<H',raw,22)[0];sram=3*n;ops=8*n
  elif schema==0x3152504d:
   k=struct.unpack_from('<H',raw,76)[0];groups=raw[74];records=groups*(k//128)
   read=records*(1152+512);sram=records*80+groups*2;ops=groups*8*k
  else:raise ValueError('missing structural cost for '+hex(schema))
  totals['ddr_read_bytes_upper']+=read;totals['ddr_write_bytes']+=write
  totals['sram_words']+=sram;totals['arithmetic_elements']+=ops
  duration=8+(read+write+15)//16+sram+ops
  ends.append(duration+max((ends[d] for d in call['after']),default=0))
 return {'work_units':max(ends,default=1),**totals,'timing_calibrated':False,
  'scope':'unit-weight structural work ranking; no runtime-cycle or throughput claim'}
