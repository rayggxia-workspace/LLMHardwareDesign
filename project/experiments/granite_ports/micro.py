"""Bounded byte/S8 microprograms. Wide arithmetic is never a native ALU op.

The Python address controller is NOT a full RTL controller. Every data arithmetic
instruction is replayable on byte_core.sv using a finite external byte store.
"""
from collections import Counter

OPCODES = {'COPY': 0, 'ADD': 1, 'SUB': 2, 'MULS8': 3, 'SHL': 4,
           'SHR': 5, 'OR': 6, 'AND': 7, 'XOR': 8, 'CMP': 9,
           'MUX': 10, 'CTRL': 11}
FRAME_BYTES = 512


def immediate(value):
    if not 0 <= value <= 255:
        raise ValueError('byte immediate')
    return -1-value


Z, ONE, FF = immediate(0), immediate(1), immediate(255)


def alu(op, a, b=0, c=0):
    if not all(type(v) is int and 0 <= v <= 255 for v in (a, b, c)):
        raise ValueError('byte operands')
    if op == 'COPY' or op == 'CTRL': return a, 0
    if op == 'ADD':
        t = a+b+(c&1); return t&255, (t >> 8)&1
    if op == 'SUB':
        t = a-b-(c&1); return t&255, int(t < 0)
    if op == 'MULS8':
        t = (a if a < 128 else a-256)*(b if b < 128 else b-256)
        return t&255, (t >> 8)&255
    if op == 'SHL': return (a << min(b, 8))&255, 0
    if op == 'SHR': return a >> min(b, 8), 0
    if op == 'OR': return a|b, 0
    if op == 'AND': return a&b, 0
    if op == 'XOR': return a^b, 0
    if op == 'CMP': return int(a < b), int(a == b)
    if op == 'MUX': return a if c&1 else b, 0
    raise ValueError('unknown byte opcode')


class Machine:
    def __init__(self, stream=None, case='tiny'):
        self.mem = [None]*FRAME_BYTES
        self.live = set()
        self.allocs = {}
        self.peak = 0
        self.hist = Counter()
        self.reads = self.writes = self.input_bytes = self.result_bytes = 0
        self.stream, self.case = stream, case
        self.emit('B '+case)

    def emit(self, text):
        if self.stream is not None: self.stream.write(text+'\n')

    def alloc(self, name, size, values=None):
        if name in self.allocs: raise ValueError('live buffer name '+name)
        for start in range(FRAME_BYTES-size+1):
            if not any(i in self.live for i in range(start, start+size)): break
        else: raise MemoryError('bounded byte frame')
        refs = list(range(start, start+size)); self.live.update(refs); self.allocs[name] = refs
        for i in refs: self.mem[i] = None
        self.peak = max(self.peak, len(self.live)); self.emit(f'M {start} {size} {name}')
        if values is not None:
            if len(values) != size: raise ValueError('input size')
            for i, value in zip(refs, values):
                if not 0 <= value <= 255: raise ValueError('byte init')
                self.mem[i] = value; self.input_bytes += 1; self.emit(f'I {i} {value}')
        return refs

    def free(self, refs):
        if not refs: return
        for key, value in list(self.allocs.items()):
            if value == refs:
                del self.allocs[key]; break
        else: raise ValueError('unknown live buffer')
        for i in refs: self.live.remove(i); self.mem[i] = None
        self.emit(f'F {refs[0]} {len(refs)}')

    def value(self, ref):
        if ref < 0: return -1-ref
        if ref not in self.live or self.mem[ref] is None: raise ValueError('uninitialized/live byte read')
        return self.mem[ref]

    def op(self, op, a=Z, b=Z, c=Z, dst=None, hi=None):
        av, bv, cv = self.value(a), self.value(b), self.value(c)
        lo, high = alu(op, av, bv, cv)
        if dst is not None:
            if dst not in self.live: raise ValueError('output not allocated')
            self.mem[dst] = lo; self.writes += 1
        if hi is not None:
            if hi not in self.live: raise ValueError('flag not allocated')
            self.mem[hi] = high; self.writes += 1
        self.hist[op] += 1; self.reads += sum(ref >= 0 for ref in (a, b, c))
        self.emit('A '+' '.join(map(str, (OPCODES[op], a, b, c, dst if dst is not None else -1,
                                          hi if hi is not None else -1, av, bv, cv, lo, high))))
        return lo, high

    def control(self, count=1):
        for _ in range(count): self.op('CTRL')

    def encoded(self, refs): return [self.value(i) for i in refs]
    def unsigned(self, refs): return int.from_bytes(bytes(self.encoded(refs)), 'little')
    def signed(self, refs): return int.from_bytes(bytes(self.encoded(refs)), 'little', signed=True)

    def output(self, name, refs, signed=False):
        self.result_bytes += len(refs)
        self.emit('O '+name+' '+str(int(signed))+' '+','.join(map(str, refs))+' '+','.join(map(str, self.encoded(refs))))
        return self.signed(refs) if signed else self.unsigned(refs)

    def finish(self):
        self.emit('E '+self.case)
        return {'primitive_counts': dict(self.hist), 'scalar_ALU_dependency_cycles': sum(self.hist.values()),
                'software_controller_dispatches': sum(self.hist.values()),
                'conservative_scalar_cycles_ALU_plus_dispatch': 2*sum(self.hist.values()),
                'byte_store_reads': self.reads, 'byte_store_writes': self.writes,
                'input_load_bytes': self.input_bytes, 'result_read_bytes': self.result_bytes, 'scratch_peak_bytes': self.peak,
                'frame_capacity_bytes': FRAME_BYTES,
                'SIMD8_qualified': False,
                'storage_note': 'finite external byte frame, not an implemented RTL RF; service must reserve/port/transport its accesses',
                'controller_note': 'one extra dispatch cycle per action is a declared candidate controller surcharge, not full-FSM RTL measurement'}


def input_value(m, name, value, width, signed=True):
    return m.alloc(name, width, list(int(value).to_bytes(width, 'little', signed=signed)))


def copy(m, src, dst):
    for a, b in zip(src, dst): m.op('COPY', a, dst=b)


def fill(m, dst, value=Z):
    for d in dst: m.op('COPY', value, dst=d)


def add(m, a, b, out, subtract=False, carry_out=None):
    flag = m.alloc('addflag', 1); m.op('COPY', Z, dst=flag[0])
    for x, y, d in zip(a, b, out):
        m.op('SUB' if subtract else 'ADD', x, y, flag[0], d, flag[0]); m.control()
    if carry_out is not None: m.op('COPY', flag[0], dst=carry_out)
    result = m.value(flag[0]); m.free(flag)
    return result


def nonzero(m, a, out):
    m.op('COPY', Z, dst=out)
    for x in a: m.op('OR', out, x, dst=out)
    flag = m.alloc('nzflag', 1); m.op('CMP', out, Z, dst=flag[0], hi=out)
    m.op('XOR', out, ONE, dst=out); m.free(flag)


def negate(m, a, out):
    tmp = m.alloc('negate', len(a))
    for x, d in zip(a, tmp): m.op('XOR', x, FF, dst=d)
    flag = m.alloc('negcarry', 1); m.op('COPY', ONE, dst=flag[0])
    for x, d in zip(tmp, out): m.op('ADD', x, Z, flag[0], d, flag[0]); m.control()
    m.free(flag); m.free(tmp)


def conditional_sign(m, a, sign, out):
    neg = m.alloc('sign_negative', len(a)); negate(m, a, neg)
    for x, y, d in zip(neg, a, out): m.op('MUX', x, y, sign, d)
    m.free(neg)


def absolute(m, a, out, sign):
    m.op('SHR', a[-1], immediate(7), dst=sign)
    conditional_sign(m, a, sign, out)


def right(m, a, amount, out, arithmetic=False):
    if not 0 <= amount <= 128: raise ValueError('right shift range')
    q, r = divmod(amount, 8)
    temp = m.alloc('righttemp', 3)
    if arithmetic:
        m.op('SHR', a[-1], immediate(7), dst=temp[2]); m.op('MUX', FF, Z, temp[2], temp[2])
    else: m.op('COPY', Z, dst=temp[2])
    for i, d in enumerate(out):
        j = i+q
        x = a[j] if j < len(a) else temp[2]
        y = a[j+1] if j+1 < len(a) else temp[2]
        m.op('SHR', x, immediate(r), dst=temp[0])
        m.op('SHL', y, immediate(8-r), dst=temp[1])
        m.op('OR', temp[0], temp[1], dst=d); m.control(2)
    m.free(temp)


def left(m, a, amount, out, signed=False):
    if not 0 <= amount <= 128: raise ValueError('left shift range')
    q, r = divmod(amount, 8)
    temp = m.alloc('lefttemp', 3)
    if signed:
        m.op('SHR', a[-1], immediate(7), dst=temp[2]); m.op('MUX', FF, Z, temp[2], temp[2])
    else: m.op('COPY', Z, dst=temp[2])
    for i, d in enumerate(out):
        j = i-q
        x = Z if j < 0 else a[j] if j < len(a) else temp[2]
        y = Z if j-1 < 0 else a[j-1] if j-1 < len(a) else temp[2]
        m.op('SHL', x, immediate(r), dst=temp[0])
        m.op('SHR', y, immediate(8-r), dst=temp[1])
        m.op('OR', temp[0], temp[1], dst=d); m.control(2)
    m.free(temp)


def guard_s32(m, a, valid_out=None):
    work = m.alloc('cast32guard', 3)
    m.op('SHR', a[3], immediate(7), dst=work[0]); m.op('MUX', FF, Z, work[0], work[0])
    m.op('COPY', Z, dst=work[1])
    for x in a[4:]:
        m.op('XOR', x, work[0], dst=work[2]); m.op('OR', work[1], work[2], dst=work[1]); m.control()
    m.op('CMP', work[1], Z, dst=work[2], hi=work[1])
    if valid_out is not None: m.op('COPY', work[1], dst=valid_out)
    valid = bool(m.value(work[1])); m.free(work)
    return valid


def signed_digits(m, a, bits, unsigned=False):
    count = 1 if bits <= 8 else 1+(bits-8+6)//7
    result = m.alloc('digits_result', count)
    current = m.alloc('digit_current', len(a)); copy(m, a, current)
    for i in range(count):
        if i == count-1: m.op('COPY', current[0], dst=result[i])
        else:
            m.op('AND', current[0], immediate(127), dst=result[i])
            nxt = m.alloc('digit_next', len(a)); right(m, current, 7, nxt, arithmetic=not unsigned)
            copy(m, nxt, current); m.free(nxt)
    m.free(current)
    return result


def multiply(m, a, b, bits_a, bits_b, out, unsigned_b=False):
    da = signed_digits(m, a, bits_a)
    # Give digit result buffers stable distinct names before second extraction.
    m.allocs['digits_a'] = m.allocs.pop('digits_result')
    db = signed_digits(m, b, bits_b, unsigned=unsigned_b)
    m.allocs['digits_b'] = m.allocs.pop('digits_result')
    p16 = m.alloc('product16', 2); wide = m.alloc('signed_product16', len(out)); shifted = m.alloc('shifted_product', len(out))
    accum = m.alloc('accum', len(out)); fill(m, accum)
    sign = m.alloc('product_sign', 1)
    for i, x in enumerate(da):
        for j, y in enumerate(db):
            m.op('MULS8', x, y, dst=p16[0], hi=p16[1])
            m.op('SHR', p16[1], immediate(7), dst=sign[0]); m.op('MUX', FF, Z, sign[0], sign[0])
            copy(m, p16, wide[:2]); fill(m, wide[2:], sign[0])
            left(m, wide, 7*(i+j), shifted, signed=True)
            if i == 0 and j == 0: copy(m, shifted, accum)
            else: add(m, accum, shifted, accum)
            m.control(2)
    copy(m, accum, out)
    for refs in (sign, accum, shifted, wide, p16, db, da): m.free(refs)


def rounded_shift(m, a, amount, out, valid_out=None):
    if not 0 <= amount <= 128: raise ValueError('RNE shift domain')
    mag = m.alloc('rne_magnitude', len(a)); sign = m.alloc('rne_sign', 1)
    absolute(m, a, mag, sign[0])
    q = m.alloc('rne_q', len(a)); right(m, mag, amount, q)
    flags = m.alloc('rne_flags', 8)
    if amount:
        index, bit = divmod(amount-1, 8)
        m.op('SHR', mag[index] if index < len(mag) else Z, immediate(bit), dst=flags[0])
        m.op('AND', flags[0], ONE, dst=flags[0])
    else: m.op('SHR', Z, immediate(0), dst=flags[0]); m.op('AND', Z, ONE, dst=flags[0])
    m.op('COPY', Z, dst=flags[1])
    for i, x in enumerate(mag):
        lower = max(0, min(8, amount-1-8*i))
        m.op('SHL', ONE, immediate(lower), dst=flags[2]); m.op('SUB', flags[2], ONE, dst=flags[2])
        m.op('AND', x, flags[2], dst=flags[3]); m.op('OR', flags[1], flags[3], dst=flags[1]); m.control(2)
    m.op('CMP', flags[1], Z, dst=flags[2], hi=flags[3]); m.op('XOR', flags[3], ONE, dst=flags[3])
    m.op('AND', q[0], ONE, dst=flags[4]); m.op('OR', flags[3], flags[4], dst=flags[4])
    m.op('AND', flags[0], flags[4], dst=flags[5])
    for x in q: m.op('ADD', x, Z, flags[5], x, flags[5]); m.control()
    conditional_sign(m, q, sign[0], out)
    valid = guard_s32(m, out, valid_out)
    for refs in (flags, q, sign, mag): m.free(refs)
    return valid


def udivide(m, numerator, denominator, quotient, remainder, valid_out=None):
    if len(numerator) != 16 or len(denominator) != 16: raise ValueError('U128 operands')
    rem = m.alloc('div_rem129', 17); div = m.alloc('div_den129', 17); trial = m.alloc('div_trial129', 17)
    shiftbuf = m.alloc('div_shift129', 17); flags = m.alloc('div_flags', 3)
    fill(m, rem); copy(m, denominator, div[:16]); m.op('COPY', Z, dst=div[16]); fill(m, quotient)
    nonzero(m, denominator, flags[0]); valid = bool(m.value(flags[0]))
    if valid_out is not None: m.op('COPY', flags[0], dst=valid_out)
    for bit in range(127, -1, -1):
        left(m, rem, 1, shiftbuf); copy(m, shiftbuf, rem)
        m.op('SHR', numerator[bit//8], immediate(bit%8), dst=flags[1]); m.op('AND', flags[1], ONE, dst=flags[1])
        m.op('OR', rem[0], flags[1], dst=rem[0])
        borrow = m.alloc('div_borrow', 1); m.op('COPY', Z, dst=borrow[0])
        for x, y, d in zip(rem, div, trial): m.op('SUB', x, y, borrow[0], d, borrow[0]); m.control()
        m.op('XOR', borrow[0], ONE, dst=flags[2]); m.free(borrow)
        for x, y, d in zip(trial, rem, rem): m.op('MUX', x, y, flags[2], d)
        m.op('SHL', flags[2], immediate(bit%8), dst=flags[1]); m.op('OR', quotient[bit//8], flags[1], dst=quotient[bit//8]); m.control(3)
    copy(m, rem[:16], remainder)
    for refs in (flags, shiftbuf, trial, div, rem): m.free(refs)
    return valid


def isqrt128(m, value, root):
    rem = m.alloc('sqrt_rem', 17); shifted = m.alloc('sqrt_shifted', 17)
    trial = m.alloc('sqrt_trial', 17); diff = m.alloc('sqrt_diff', 17); rootbuf = m.alloc('sqrt_rootshift', 8)
    flags = m.alloc('sqrt_flags', 3); fill(m, rem); fill(m, root)
    for pair in range(63, -1, -1):
        left(m, rem, 2, shifted); copy(m, shifted, rem)
        m.op('SHR', value[(2*pair)//8], immediate((2*pair)%8), dst=flags[0]); m.op('AND', flags[0], immediate(3), dst=flags[0])
        m.op('OR', rem[0], flags[0], dst=rem[0])
        left(m, root, 2, trial); m.op('OR', trial[0], ONE, dst=trial[0])
        borrow = m.alloc('sqrt_borrow', 1); m.op('COPY', Z, dst=borrow[0])
        for x, y, d in zip(rem, trial, diff): m.op('SUB', x, y, borrow[0], d, borrow[0]); m.control()
        m.op('XOR', borrow[0], ONE, dst=flags[1]); m.free(borrow)
        for x, y, d in zip(diff, rem, rem): m.op('MUX', x, y, flags[1], d)
        left(m, root, 1, rootbuf); copy(m, rootbuf, root); m.op('OR', root[0], flags[1], dst=root[0]); m.control(3)
    for refs in (flags, rootbuf, diff, trial, shifted, rem): m.free(refs)


def rounded_divide(m, numerator, denominator64, out, valid_out):
    mag = m.alloc('rdiv_magnitude', 16); sign = m.alloc('rdiv_sign', 1); absolute(m, numerator, mag, sign[0])
    den = m.alloc('rdiv_den128', 16); copy(m, denominator64, den[:8]); fill(m, den[8:])
    q, r = m.alloc('rdiv_q', 16), m.alloc('rdiv_r', 16)
    valid = udivide(m, mag, den, q, r, valid_out)
    twice = m.alloc('rdiv_twice129', 17); den129 = m.alloc('rdiv_den129', 17)
    left(m, r, 1, twice); copy(m, den, den129[:16]); m.op('COPY', Z, dst=den129[16])
    delta = m.alloc('rdiv_delta', 17); borrow = m.alloc('rdiv_borrow', 1); m.op('COPY', Z, dst=borrow[0])
    for x, y, d in zip(twice, den129, delta): m.op('SUB', x, y, borrow[0], d, borrow[0]); m.control()
    flags = m.alloc('rdiv_flags', 4); nonzero(m, delta, flags[0])
    m.op('XOR', borrow[0], ONE, dst=flags[1]); m.op('AND', flags[0], flags[1], dst=flags[2])
    m.op('XOR', flags[0], ONE, dst=flags[0]); m.op('AND', q[0], ONE, dst=flags[3]); m.op('AND', flags[0], flags[3], dst=flags[3])
    m.op('OR', flags[2], flags[3], dst=flags[2])
    for x in q: m.op('ADD', x, Z, flags[2], x, flags[2]); m.control()
    conditional_sign(m, q, sign[0], out)
    castvalid = m.alloc('rdiv_castvalid', 1)
    guard_s32(m, out, castvalid[0]); m.op('AND', valid_out, castvalid[0], dst=valid_out)
    valid = bool(m.value(valid_out)); m.free(castvalid)
    for refs in (flags, borrow, delta, den129, twice, r, q, den, sign, mag): m.free(refs)
    return valid


OP_SPECS = {
    'mul_s32_s32': {'input': ['S32', 'S32'], 'output': 'S64', 'digit_products': 25},
    'mul_s64_s32': {'input': ['S64', 'S32'], 'output': 'S128', 'digit_products': 45},
    'mul_s32_u16': {'input': ['S32', 'U16'], 'output': 'S64', 'digit_products': 15},
    'add_s64': {'input': ['S64', 'S64'], 'output': 'S64', 'overflow': 'reject'},
    'sub_s64': {'input': ['S64', 'S64'], 'output': 'S64', 'overflow': 'reject'},
    'add_u128': {'input': ['U128', 'U128'], 'output': 'U128', 'overflow': 'reject'},
    'abs_s64': {'input': ['S64'], 'output': 'U64'},
    'max_s64': {'input': ['S64', 'S64'], 'output': 'S64'},
    'cmp_s64': {'input': ['S64', 'S64'], 'output': 'less/equal'},
    'align_s32_i64': {'input': ['S32', 'shift0..63'], 'output': 'S64', 'overflow': 'reject'},
    'shl_s64_s128': {'input': ['S64', 'shift0..127'], 'output': 'S128', 'overflow': 'reject'},
    'shl_u128': {'input': ['U128', 'shift0..127'], 'output': 'U128', 'overflow': 'reject'},
    'rne_s64_i32': {'input': ['S64', 'shift0..128'], 'output': 'S32', 'overflow': 'reject', 'rounding': 'symmetric RNE'},
    'rne_s128_i32': {'input': ['S128', 'shift0..128'], 'output': 'S32', 'overflow': 'reject', 'rounding': 'symmetric RNE'},
    'udiv_u128': {'input': ['U128', 'U128'], 'output': 'U128 quotient/remainder', 'zero_divisor': 'reject'},
    'isqrt_u128': {'input': ['U128'], 'output': 'U64 floor sqrt'},
    'div_rne_s128_u64_i32': {'input': ['S128', 'U64'], 'output': 'S32', 'overflow_or_zero': 'reject', 'rounding': 'symmetric RNE'},
}


def equal_bytes(m, a, b, valid_out=None):
    flags = m.alloc('equality', 3); m.op('COPY', Z, dst=flags[0])
    for x, y in zip(a, b):
        m.op('XOR', x, y, dst=flags[1]); m.op('OR', flags[0], flags[1], dst=flags[0]); m.control()
    m.op('CMP', flags[0], Z, dst=flags[1], hi=flags[2])
    if valid_out is not None: m.op('COPY', flags[2], dst=valid_out)
    result = bool(m.value(flags[2])); m.free(flags); return result


def execute(op, a, b=0, shift=0, stream=None, case='tiny'):
    if op not in OP_SPECS: raise ValueError('unregistered operation')
    m = Machine(stream, case)
    publish = m.alloc('publish_valid', 1, [1])
    valid = True
    if op.startswith('mul_'):
        abits = 64 if op == 'mul_s64_s32' else 32
        bbits = 16 if op == 'mul_s32_u16' else 32
        aa = input_value(m, 'input_a', a, abits//8)
        bb = input_value(m, 'input_b', b, bbits//8, signed=op != 'mul_s32_u16')
        out = m.alloc('output', 16 if abits == 64 else 8)
        multiply(m, aa, bb, abits, bbits, out, unsigned_b=op == 'mul_s32_u16')
        result = {'value': m.signed(out)}
    elif op in ('add_s64', 'sub_s64', 'add_u128'):
        width, signed = (8, True) if op in ('add_s64', 'sub_s64') else (16, False)
        aa = input_value(m, 'input_a', a, width, signed); bb = input_value(m, 'input_b', b, width, signed)
        out = m.alloc('output', width); carry = add(m, aa, bb, out, subtract=op == 'sub_s64', carry_out=publish[0])
        if signed:
            flags = m.alloc('addsigns', 4)
            for src, dst in zip((aa[-1], bb[-1], out[-1]), flags): m.op('SHR', src, immediate(7), dst=dst)
            if op == 'sub_s64':
                m.op('XOR', flags[0], flags[1], dst=flags[1]); m.op('XOR', flags[0], flags[2], dst=flags[0])
            else:
                m.op('XOR', flags[0], flags[2], dst=flags[0]); m.op('XOR', flags[1], flags[2], dst=flags[1])
            m.op('AND', flags[0], flags[1], dst=flags[3]); m.op('XOR', flags[3], ONE, dst=publish[0]); m.free(flags)
        else: m.op('XOR', publish[0], ONE, dst=publish[0])
        result = {'value': m.signed(out) if signed else m.unsigned(out)}
    elif op == 'abs_s64':
        aa = input_value(m, 'input_a', a, 8); out = m.alloc('output', 8); sign = m.alloc('abs_sign', 1)
        absolute(m, aa, out, sign[0]); result = {'value': m.unsigned(out)}
    elif op in ('cmp_s64', 'max_s64'):
        aa = input_value(m, 'input_a', a, 8); bb = input_value(m, 'input_b', b, 8)
        ac = m.alloc('cmpa', 8); bc = m.alloc('cmpb', 8); copy(m, aa, ac); copy(m, bb, bc)
        m.op('XOR', ac[-1], immediate(128), dst=ac[-1]); m.op('XOR', bc[-1], immediate(128), dst=bc[-1])
        out = m.alloc('cmp_sub', 8); compare_flags = m.alloc('compare_result', 2)
        add(m, ac, bc, out, subtract=True, carry_out=compare_flags[0]); equal_bytes(m, aa, bb, compare_flags[1])
        if op == 'max_s64':
            for x, y, dst in zip(bb, aa, out): m.op('MUX', x, y, compare_flags[0], dst)
            result = {'value': m.signed(out)}
        else: result = {'less': bool(m.value(compare_flags[0])), 'equal': bool(m.value(compare_flags[1]))}
    elif op in ('align_s32_i64', 'shl_s64_s128', 'shl_u128'):
        width = 4 if op == 'align_s32_i64' else 8 if op == 'shl_s64_s128' else 16
        limit = 63 if op == 'align_s32_i64' else 127
        if not 0 <= shift <= limit: raise ValueError('declared left shift domain')
        signed = op != 'shl_u128'; outwidth = 8 if op == 'align_s32_i64' else 16
        aa = input_value(m, 'input_a', a, width, signed); out = m.alloc('output', outwidth)
        left(m, aa, shift, out, signed=signed)
        inverse = m.alloc('inverse_shift', outwidth); right(m, out, shift, inverse, arithmetic=signed)
        extended = m.alloc('extended_input', outwidth); left(m, aa, 0, extended, signed=signed)
        valid = equal_bytes(m, inverse, extended, publish[0])
        result = {'value': m.signed(out) if signed else m.unsigned(out)}
    elif op in ('rne_s64_i32', 'rne_s128_i32'):
        width = 8 if op == 'rne_s64_i32' else 16
        aa = input_value(m, 'input_a', a, width); out = m.alloc('output', width)
        valid = rounded_shift(m, aa, shift, out, publish[0]); result = {'value': m.signed(out)}
    elif op == 'udiv_u128':
        aa = input_value(m, 'input_a', a, 16, False); bb = input_value(m, 'input_b', b, 16, False)
        out, rem = m.alloc('quotient', 16), m.alloc('remainder', 16)
        valid = udivide(m, aa, bb, out, rem, publish[0]); result = {'quotient': m.unsigned(out), 'remainder': m.unsigned(rem)}
    elif op == 'isqrt_u128':
        aa = input_value(m, 'input_a', a, 16, False); out = m.alloc('output', 8)
        isqrt128(m, aa, out); result = {'value': m.unsigned(out)}
    else:
        aa = input_value(m, 'input_a', a, 16); bb = input_value(m, 'input_b', b, 8, False); out = m.alloc('output', 16)
        valid = rounded_divide(m, aa, bb, out, publish[0]); result = {'value': m.signed(out)}
    if op == 'udiv_u128':
        m.output('quotient', out); m.output('remainder', rem)
    elif op == 'cmp_s64':
        m.output('less', compare_flags[:1]); m.output('equal', compare_flags[1:])
    else:
        m.output('value', out, signed=OP_SPECS[op]['output'].startswith('S'))
    result['valid'] = bool(m.output('valid', publish))
    return result, m.finish()
