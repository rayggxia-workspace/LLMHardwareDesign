"""GTH2: runtime signed 32/64-bit index, power-of-two table row, selected slice."""
import struct,zlib
def encode(*,topology,table_address,index_address,rows,row_shift,index_bytes,offset,byte_count,sram_word):
 values=(topology,table_address,index_address,rows,row_shift,index_bytes,offset,byte_count,sram_word)
 if any(type(v) is not int for v in values):raise ValueError('integer Gather fields')
 if not 0<topology<2**32 or not 0<rows<2**32 or not 6<=row_shift<=24 or index_bytes not in (4,8):
  raise ValueError('Gather geometry')
 if table_address<0 or table_address%64 or table_address+(rows<<row_shift)>1<<48:
  raise ValueError('Gather table aperture')
 if index_address<0 or index_address%index_bytes or index_address+index_bytes>1<<48:
  raise ValueError('Gather index aperture')
 if not 0<byte_count<=16384 or byte_count%64 or offset<0 or offset%64 or offset+byte_count>1<<row_shift:
  raise ValueError('Gather slice')
 if sram_word<0 or sram_word+byte_count//16>1024:raise ValueError('Gather SRAM')
 raw=bytearray(128)
 struct.pack_into('<IHHIIQQIIHHBB',raw,0,0x32485447,128,1,0x02504402,topology,
  table_address,index_address,rows,offset,byte_count,sram_word,row_shift,index_bytes)
 struct.pack_into('<I',raw,124,zlib.crc32(raw[:124]))
 return bytes(raw)
