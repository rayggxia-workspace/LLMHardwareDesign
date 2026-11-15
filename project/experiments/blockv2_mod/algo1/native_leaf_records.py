"""Fresh native records for the U/C/F lane-command RTL ABI.

These records encode one concrete operation after operand allocation. They do
not turn a finite_loop count tree into an executable program by themselves.
"""
COMMAND = 0x100

def unsigned(value, bits, name):
    if type(value) is not int or not 0 <= value < 1 << bits:
        raise ValueError(name + ' outside native field')
    return value

def lane_command(*, lanes, lane, meta, sources=(), destination=None):
    unsigned(lanes, 3, 'lanes')
    if not 1 <= lanes <= 4 or type(lane) is not int or not 0 <= lane < lanes:
        raise ValueError('lane absent from target')
    if len(sources) > 2:
        raise ValueError('ordinary lane command allows at most two inputs')
    unsigned(meta, 64, 'meta')
    for address in sources: unsigned(address, 10, 'source address')
    native0 = lane | len(sources) << 2
    if destination is not None:
        native0 |= 16 | unsigned(destination, 10, 'destination address') << 5
    # C R256 LOAD row validation mirrors the native adapter's actual acceptance.
    if lanes == 3 and lane == 2 and meta & 3 == 0:
        region, index = (meta >> 2) & 7, (meta >> 5) & 1023
        if index >= (64,64,4,4,6,1,6,4)[region]:
            raise ValueError('R256 load row would alias physical state')
    return COMMAND, (native0, sum(v << (10*i) for i,v in enumerate(sources)),
                     meta & 0xffffffff, meta >> 32)

def e32_command(*, op, sources, destination=None, mask=15, shift=0, minus=0):
    unsigned(op, 4, 'E32 operation')
    if op > 11: raise ValueError('unsupported E32 operation')
    expected = 1 if op in (3,4,10,11) else 3 if op in (1,9) else 2
    if len(sources) != expected: raise ValueError('E32 operand count differs from operation')
    if type(shift) is not int or not -63 <= shift <= 63:
        raise ValueError('invalid E32 shift')
    if op not in (2,3,4) and shift: raise ValueError('operation does not accept shift')
    unsigned(mask, 4, 'lane mask')
    unsigned(minus, 3, 'sign mask')
    if op > 1 and minus or op == 0 and minus & 4:
        raise ValueError('operation does not accept sign mask')
    for address in sources: unsigned(address, 10, 'source address')
    native0 = 1 << 15 | len(sources) << 2
    if destination is not None:
        native0 |= 16 | unsigned(destination, 10, 'destination address') << 5
    return COMMAND, (native0, sum(v << (10*i) for i,v in enumerate(sources)),
                     op | mask << 4 | (shift & 255) << 8 | minus << 16, 0)
