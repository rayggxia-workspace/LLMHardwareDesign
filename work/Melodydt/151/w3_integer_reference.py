"""Independent mathematical integer oracle for the bounded W3 FFN8 profile.

LUT values are rebuilt from the generating mathematical functions. The native
table is only parsed by validate_native_table to verify source/version equality;
it is never the oracle input and no DUT result is consulted.
"""
import math
import re


def signed(value, bits):
    value &= (1 << bits) - 1
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def rne(value, shift):
    if not shift:
        return value
    q, remainder = divmod(value, 1 << shift)
    half = 1 << (shift - 1)
    return q + int(remainder > half or (remainder == half and q & 1))


def clip(value, bits=16):
    lo, hi = -(1 << (bits - 1)), (1 << (bits - 1)) - 1
    return max(lo, min(hi, value)), not lo <= value <= hi


def pack(values, bits):
    return sum((int(v) & ((1 << bits) - 1)) << (bits * i) for i, v in enumerate(values))


def unpack(word, bits, count):
    return [signed(word >> (bits*i), bits) for i in range(count)]


def activation_function(fn, x):
    if fn == 0:
        return x / (1 + math.exp(-x))
    if fn == 1:
        return 1 / (1 + math.exp(-x))
    if fn == 2:
        return .5*x*(1 + math.tanh(math.sqrt(2/math.pi)*(x + .044715*x*x*x)))
    if fn == 3:
        return math.log1p(math.exp(x))
    raise ValueError('unsupported mathematical activation')


MATH_TABLES = {}
for _fn in range(4):
    _limit = 16 if _fn == 3 else 8
    MATH_TABLES[_fn] = [round(activation_function(_fn, -_limit + i/32) * (16384 if _fn == 1 else 1024)) for i in range(_limit*64+1)]


def validate_native_table(text):
    parsed = {}
    for key, sign, magnitude in re.findall(r"13'd(\d+):\s*activation_lut=(-?)16'sd(\d+);", text):
        parsed[int(key)] = (-1 if sign else 1) * int(magnitude)
    expected = {(fn << 11) | i: value for fn, table in MATH_TABLES.items() for i, value in enumerate(table)}
    if parsed != expected:
        mismatches = [(k, expected.get(k), parsed.get(k)) for k in sorted(set(expected) | set(parsed)) if expected.get(k) != parsed.get(k)]
        raise AssertionError('math table differs from frozen native table: {}'.format(mismatches[:8]))
    return {'mathematical_nodes': len(expected), 'parsed_nodes': len(parsed), 'equal_all_nodes': True, 'node_counts': [len(MATH_TABLES[fn]) for fn in range(4)]}


def g_activation(fn, x):
    if fn not in range(4):
        return 0
    limit = 16384 if fn == 3 else 8192
    if x < -limit:
        return 0
    if x > limit:
        return 16384 if fn == 1 else x
    offset = x + limit
    index, fraction = divmod(offset, 32)
    table = MATH_TABLES[fn]
    lo, hi = table[index], table[min(index+1, len(table)-1)]
    return lo + rne((hi-lo)*fraction, 5)


def g_vector(fn, gated, x, gate, count):
    if not 1 <= count <= 8:
        return {'error': True, 'saturated': False, 'output': [0]*8}
    if fn not in range(4):
        return {'error': True, 'saturated': False, 'output': [0]*8}
    result, saturation = [], False
    for i in range(count):
        y = g_activation(fn, x[i])
        if gated:
            y = rne(y*gate[i], 14 if fn == 1 else 10)
        value, sat = clip(y)
        result.append(value)
        saturation |= sat
    return {'error': False, 'saturated': saturation, 'output': result + [0]*(8-count)}


E_MASKS = {0:'AB',1:'AB',2:'AB',3:'ABC',4:'AB',5:'AB',6:'ABC',7:'A',8:'A',9:'AB',10:'A',11:'A',12:'A',13:'A'}


def e_vector(op, shift, a, b, c, count):
    if not 1 <= count <= (4 if op == 13 else 8) or (op == 9 and count % 2) or op > 13:
        return {'error': True, 'saturated': False, 'output_word': 0}
    out, saturation = [], False
    a, b, c = [list(v) + [0]*(8-len(v)) for v in (a,b,c)]
    for i in range(count):
        av, bv, cv = a[i], b[i], c[i]
        if op == 0: value = av+bv
        elif op == 1: value = av-bv
        elif op == 2: value = rne(av*bv, shift)
        elif op == 3: value = rne(av*bv+cv, shift)
        elif op == 4: value = max(av,bv)
        elif op == 5: value = min(av,bv)
        elif op == 6: value = av if cv else bv
        elif op == 7: value = av << shift
        elif op == 8: value = av >> shift
        elif op == 9:
            even = i & ~1
            value = rne(a[even]*b[even]-a[even+1]*b[even+1] if i%2 == 0 else a[even+1]*b[even]+a[even]*b[even+1], shift)
        elif op in (10,13): value = rne(av,shift)
        elif op == 11: value = abs(av)
        elif op == 12: value = av
        value, sat = clip(value, 8 if op == 12 else 16)
        out.append(value);saturation |= sat
    return {'error':False, 'saturated':saturation, 'output_word':pack(out,8 if op == 12 else 16), 'output':out}


def matrix(a, columns, shift):
    raw = [sum(a[k]*col[k] for k in range(8)) for col in columns]
    values, saturation = [], False
    for value in raw:
        narrowed, sat = clip(rne(value,shift));values.append(narrowed);saturation |= sat
    return raw, values, saturation


def ffn8(x, gate_weights, up_weights, down_weights):
    for values in [x] + gate_weights + up_weights + down_weights:
        assert len(values) == 8 and all(-128 <= v <= 127 for v in values)
    gate_raw, gate, sg = matrix(x, gate_weights, 4)
    up_raw, up, su = matrix(x, up_weights, 4)
    mid_result = g_vector(0, True, gate, up, 8)
    mid = mid_result['output']
    down_raw, down, sd = matrix(mid, down_weights, 7)
    residual = [v << 3 for v in x]
    final_result = e_vector(0,0,down,residual,[0]*8,8)
    final = final_result['output']
    words = [pack(x,8),0,0,0]
    for weights in [gate_weights,up_weights,down_weights]:
        packed = pack([v for col in weights for v in col],8)
        words += [(packed >> (128*i)) & ((1<<128)-1) for i in range(4)]
    stages = {464:pack(gate,16),465:pack(up,16),466:pack(x,16),467:pack(residual,16),468:pack(mid,16),469:0,470:0,471:0,472:pack(down,16),473:pack(final,16)}
    return {'ingress_words':words,'raw_gate':gate_raw,'raw_up':up_raw,'gate':gate,'up':up,'residual':residual,'mid':mid,'raw_down':down_raw,'down':down,'final':final,'S_words':stages,'stage_saturated':{'gate_M':sg,'up_M':su,'G_mid':mid_result['saturated'],'down_M':sd,'E_residual_shift':False,'E_final_add':final_result['saturated']},'done_saturated':sg or su or mid_result['saturated'] or sd or final_result['saturated'],'done_error':False}
