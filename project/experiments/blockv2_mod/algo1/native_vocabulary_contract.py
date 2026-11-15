"""Encode automatic vocabulary phase control in the P service descriptor."""
import struct
import zlib


def lower_vocabulary(raw, *, step, topology):
    if len(raw)!=128 or not 0 <= step < 1<<32:
        raise ValueError("invalid vocabulary descriptor extent or step")
    schema,size,opcode,abi,base=struct.unpack_from("<IHHII",raw)
    if (schema,size,opcode,abi,base)!=(0x02505001,128,2,0x02504d02,topology):
        raise ValueError("unexpected vocabulary compute ABI")
    if zlib.crc32(raw[:124])!=int.from_bytes(raw[124:],"little") or any(raw[112:124]):
        raise ValueError("invalid vocabulary descriptor seal or reserved fields")
    result=bytearray(raw)
    struct.pack_into("<H",result,6,3)
    struct.pack_into("<I",result,112,step)
    struct.pack_into("<I",result,124,zlib.crc32(result[:124]))
    return bytes(result)
