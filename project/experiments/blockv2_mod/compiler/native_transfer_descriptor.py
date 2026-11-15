"""Counted DDR/SRAM moves for native view materialization."""
import struct,zlib
ABI=0x02500002
def encode(*, direction, topology, sram_word, address, byte_count, first_tag=0):
    if direction not in ('load','store'):raise ValueError('unknown transfer direction')
    if any(type(x) is not int for x in (topology,sram_word,address,byte_count,first_tag)):
        raise ValueError('integer transfer fields required')
    beat=128 if direction=='load' else 64
    if not 0<topology<2**32 or not 0<byte_count<=8192 or byte_count%beat:
        raise ValueError('transfer length/topology')
    if not 0<=sram_word<=1024-byte_count//16 or address%beat or not 0<=address<=(1<<(48 if direction=='load' else 64))-byte_count:
        raise ValueError('transfer source/destination bounds')
    if not 0<=first_tag<=(1<<64)-byte_count//64 or direction=='load' and first_tag:
        raise ValueError('transfer tag bounds')
    raw=bytearray(128);schema=int.from_bytes(b'DLC1' if direction=='load' else b'DSC1','little')
    struct.pack_into('<IHHIIHHIQ',raw,0,schema,128,1,ABI,topology,sram_word,byte_count//beat,0,address)
    if direction=='store':struct.pack_into('<Q',raw,32,first_tag)
    struct.pack_into('<I',raw,124,zlib.crc32(raw[:124]))
    return bytes(raw)
