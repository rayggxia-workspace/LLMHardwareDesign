"""Encode the descriptor-started projection activation supplier."""
import struct
import zlib
SCHEMA=int.from_bytes(b'PFED','little')
ABI=0x02500002

def encode(*,topology,source_word,scratch_word,destination_word,elements,input_key,session,first_k=0):
    fields=(topology,source_word,scratch_word,destination_word,elements,input_key,session,first_k)
    if any(type(x) is not int for x in fields):raise ValueError('integer descriptor fields required')
    if not 0<topology<2**32 or not 0<input_key<2**128 or not 0<session<2**32:
        raise ValueError('invalid service identity')
    if elements<=0 or elements%128 or elements>4096:
        raise ValueError('projection supply requires bounded 128-element tiles')
    if first_k<0 or first_k%128 or first_k+elements>65535:
        raise ValueError('projection K range outside descriptor extent')
    words=elements//4
    if not 0<=source_word<=1024-words or not 0<=scratch_word<=1008 or not 0<=destination_word<=1008:
        raise ValueError('projection supply exceeds SRAM')
    if source_word<scratch_word+16 and scratch_word<source_word+words:
        raise ValueError('quantization scratch overlaps live activation')
    raw=bytearray(128)
    struct.pack_into('<IHHII4H',raw,0,SCHEMA,128,2 if first_k else 1,ABI,topology,
                     source_word,scratch_word,destination_word,elements//128)
    raw[24:40]=input_key.to_bytes(16,'little')
    struct.pack_into('<I',raw,40,session)
    struct.pack_into('<H',raw,44,first_k)
    struct.pack_into('<I',raw,124,zlib.crc32(raw[:124]))
    return bytes(raw)
