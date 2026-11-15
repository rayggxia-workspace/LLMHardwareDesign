"""Fixed descriptor-fetch kernel; generated once per hardware deployment.

Operands and operation selection live in each CALL's descriptor. This image
contains no operator ordering, model shape, weight address, or selected plan.
"""
import struct
import zlib
from hashlib import sha256

def encode(*, topology, image_id=25001):
    if type(topology) is not int or not 0 < topology < 2**32:
        raise ValueError('invalid topology')
    if type(image_id) is not int or not 0 < image_id < 2**32:
        raise ValueError('invalid image identity')
    data=bytearray(352)
    def field(bit,width,value):
        data[bit//8:(bit+width)//8]=value.to_bytes(width//8,'little')
    for bit,width,value in [
        (0,64,0x313041534943424c),(64,16,2),(80,8,1),(88,8,8),
        (96,32,352),(160,32,3),(192,32,128),(224,16,1),(256,16,1),
        (288,32,160),(352,32,224),(416,32,3),(448,32,1),
        (480,32,image_id),(512,32,topology),(544,32,0x02500002),(672,32,0x02510001),
    ]:field(bit,width,value)
    # EXEC descriptor-fetch service; WAIT its completion; RETURN.
    struct.pack_into('<QQQ',data,128,0x4100000000000000,0x4400000000000001,0x4f00000000000000)
    for off,bit,width,value in [
        (160,0,16,1),(160,128,32,3),(160,160,32,1),
        (160,192,32,image_id),(160,224,32,topology),(160,352,32,0x02500002),
        (224,0,32,1),(224,32,16,0x0250),(224,64,32,0xffffffff),
        (224,160,48,0xffffffffffff),(224,448,32,0x02500002),
    ]:field(off*8+bit,width,value)
    return bytes(data)

def manifest(data, *, topology, target):
    return {'target':target,'topology':topology,'bytes':len(data),
            'abi':0x02500002,'capacity':0x02510001,
            'crc32':zlib.crc32(data),'sha256':sha256(data).hexdigest(),
            'lifetime':'deployment','operands':'per-CALL DDR descriptor'}


def validate(data, *, topology, image_id):
    # The TLM implements this specific EXEC -> WAIT -> RETURN kernel.
    # A sealed but different program must not silently receive those semantics.
    if data != encode(topology=topology, image_id=image_id):
        raise ValueError('local program is not the supported descriptor EXEC/WAIT/RETURN kernel')
    return True
