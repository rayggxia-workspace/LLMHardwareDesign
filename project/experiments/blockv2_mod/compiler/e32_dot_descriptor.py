"""EMD1 strided signed S32 dot: four outputs, full-K RNE, optional E32 scaling."""
import struct,zlib
SCHEMA=int.from_bytes(b'EMD1','little')
ABI=0x02504503
def encode(*,topology,k,columns,shift,result_word,a_address,b_address,
           a_stride=4,b_k_stride=4,b_column_stride=0,scale=None,scale_shift=0):
    values=(topology,k,columns,shift,result_word,a_address,b_address,a_stride,b_k_stride,b_column_stride,scale_shift)
    if any(type(v) is not int for v in values):raise ValueError('integer dot descriptor fields required')
    if not 0<topology<2**32 or not 1<=k<=65535 or not 1<=columns<=4 or not 0<=shift<=63 or not 0<=result_word<1024:
        raise ValueError('dot shape/shift/result bounds')
    for stride in (a_stride,b_k_stride,b_column_stride):
        if not 0<=stride<2**32 or stride%4:raise ValueError('S32 byte stride')
    for addr,extent in ((a_address,(k-1)*a_stride+4),(b_address,(k-1)*b_k_stride+(columns-1)*b_column_stride+4)):
        if addr%4 or not 0<=addr<=(1<<48)-extent:raise ValueError('48-bit S32 operand extent')
    if scale is None:
        if scale_shift:raise ValueError('unused scale shift')
    elif type(scale) is not int or not -(1<<31)<=scale<(1<<31) or not 0<=scale_shift<=63:
        raise ValueError('S32 post-scale coefficient/shift')
    d=bytearray(128)
    struct.pack_into('<IHHIIHBBHHQQIII',d,0,SCHEMA,128,1,ABI,topology,k,columns,shift,result_word,0,
                     a_address,b_address,a_stride,b_k_stride,b_column_stride)
    struct.pack_into('<BBHi',d,52,int(scale is not None),scale_shift,0,0 if scale is None else scale)
    struct.pack_into('<I',d,124,zlib.crc32(d[:124]))
    return bytes(d)
