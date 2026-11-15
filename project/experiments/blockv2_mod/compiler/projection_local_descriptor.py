"""MPR1: native projection scope with an explicit contiguous S32 DDR source."""
import struct,zlib
SCHEMA=int.from_bytes(b'MPR1','little')
ABI=0x02504D03

def encode(scope,*,source_address,source_word):
    if not isinstance(scope,bytes) or len(scope)!=128:
        raise ValueError('one native projection scope required')
    schema,length,op,abi,topology=struct.unpack_from('<IHHII',scope)
    if (schema,length,op,abi)!=(0x02505001,128,2,0x02504d02) or not topology:
        raise ValueError('unsupported native M scope')
    if zlib.crc32(scope[:124])!=int.from_bytes(scope[124:],'little'):
        raise ValueError('scope CRC')
    k,k_begin,k_end=struct.unpack_from('<HHH',scope,76)
    a_word,out_word=struct.unpack_from('<HH',scope,84)
    groups=scope[74];ways=scope[82]
    if not k or k%128 or k_begin or k_end!=k or ways!=1:
        raise ValueError('local input requires a complete single-way projection')
    if any(scope[112:124]):raise ValueError('scope extension is not unused')
    if type(source_address) is not int or source_address%64 or not 0<=source_address<=(1<<48)-k*4:
        raise ValueError('input DDR extent/alignment')
    if type(source_word) is not int or not 0<=source_word<=992:
        raise ValueError('input staging exceeds SRAM')
    ranges=[(source_word,source_word+32),(a_word,a_word+16),(out_word,out_word+groups*2)]
    if any(a<d and c<b for i,(a,b) in enumerate(ranges) for c,d in ranges[i+1:]):
        raise ValueError('live input/quantized/output SRAM windows overlap')
    raw=bytearray(scope)
    struct.pack_into('<I',raw,0,SCHEMA);struct.pack_into('<I',raw,8,ABI)
    struct.pack_into('<QHH',raw,112,source_address,source_word,0)
    struct.pack_into('<I',raw,124,zlib.crc32(raw[:124]))
    return bytes(raw)
