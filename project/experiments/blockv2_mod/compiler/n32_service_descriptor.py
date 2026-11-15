"""NSV1 commands for the explicit N32 mod service; no macro instance selection."""
import struct
import zlib

SCHEMA=int.from_bytes(b'NSV1','little')
ABI=0x02504E03
OPERATIONS={'Softmax':1,'RMSFactor':2,'Argmax':3}

def encode(*,operation,topology,source_word,elements,result_word=None,
           epsilon_mantissa=0,epsilon_shift=0,baseline_shift=0):
    if operation not in OPERATIONS:raise ValueError('unknown N32 operation')
    values=(topology,source_word,elements,epsilon_mantissa,epsilon_shift,baseline_shift)
    if any(type(x) is not int for x in values):raise ValueError('integer command fields required')
    if not 0<topology<2**32 or not 1<=elements<=4096 or not 0<=source_word<=1024-(elements+3)//4:
        raise ValueError('N32 topology or SRAM range')
    if not -32<=baseline_shift<=31 or not -128<=epsilon_shift<=127 or not 0<=epsilon_mantissa<2**32:
        raise ValueError('N32 fixed-point parameter range')
    if operation=='RMSFactor':
        if epsilon_mantissa==0:raise ValueError('RMS epsilon must be positive')
    elif any((epsilon_mantissa,epsilon_shift,baseline_shift)):
        raise ValueError('unused N32 parameters must be zero')
    if operation=='Softmax':
        if result_word is not None:raise ValueError('Softmax commits in place')
        result_word=0xffff
    elif type(result_word) is not int or not 0<=result_word<1024:
        raise ValueError('scalar result needs an allocated SRAM word')
    raw=bytearray(128)
    struct.pack_into('<IHHII',raw,0,SCHEMA,128,OPERATIONS[operation],ABI,topology)
    struct.pack_into('<HHIbbH',raw,16,source_word,elements,epsilon_mantissa,
                     baseline_shift,epsilon_shift,result_word)
    struct.pack_into('<I',raw,124,zlib.crc32(raw[:124]))
    return bytes(raw)

def decode_result(raw,operation):
    if operation not in ('RMSFactor','Argmax') or not isinstance(raw,bytes) or len(raw)!=16:
        raise ValueError('N32 scalar result format')
    scalar,index,shift,extra,mode=struct.unpack_from('<IIbBB',raw)
    if any(raw[11:]) or mode!=OPERATIONS[operation]-1 or not -32<=shift<=31 or extra>63:
        raise ValueError('N32 result does not match its command')
    if operation=='RMSFactor':
        if index:raise ValueError('RMS result carries an unexpected index')
        return {'factor':scalar,'shift':shift,'extra_shift':extra}
    if scalar>=2**31:scalar-=2**32
    return {'maximum':scalar,'index':index}
