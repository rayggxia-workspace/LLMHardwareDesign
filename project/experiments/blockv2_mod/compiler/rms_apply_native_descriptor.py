"""RMA1 consumes the committed NSV1 factor packet from selected SRAM."""
import struct,zlib
def encode(*,topology,x_word,gamma_word,words,factor_word,gamma_shift=16):
 if any(type(v) is not int for v in (topology,x_word,gamma_word,words,factor_word,gamma_shift)):
  raise ValueError('integer RMS application fields')
 if not 0<topology<2**32 or not 0<words<1024 or not -63<=gamma_shift<=63:
  raise ValueError('RMS application header')
 ranges=[(x_word,x_word+words),(gamma_word,gamma_word+words),(factor_word,factor_word+1)]
 if any(a<0 or b>1024 for a,b in ranges) or any(a<d and c<b for i,(a,b) in enumerate(ranges) for c,d in ranges[i+1:]):
  raise ValueError('RMS application live SRAM windows')
 raw=bytearray(128)
 struct.pack_into('<IHHII4Hb',raw,0,0x31414d52,128,1,0x02504504,topology,
  x_word,gamma_word,words,factor_word,gamma_shift)
 struct.pack_into('<I',raw,124,zlib.crc32(raw[:124]))
 return bytes(raw)
