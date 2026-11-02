"""Independent periodic-input N-long math; Python3.7, no DUT-output input.

RMS/L2 whole-group statistics, exact U16 EXP and per-lane RNE are mathematical
expectations. Periodicity compresses literal expected words without shortening
the real group. The final active element changes the global statistic/max.
"""
import math

PATTERN = [-1024, 1024, 2048, -2048, 3, -3, 7, -7]
GAMMA = [1024, -1024, 512, -512, 2048, -2048, 0, 32767]
CASES = [
    ('NL_RMS1024_GLOBAL_LAST', 1, 1024, 'pattern', 30000),
    ('NL_RMS1023_TAIL7', 1, 1023, 'pattern', -32768),
    ('NL_RMS513_TAIL1', 1, 513, 'pattern', 32767),
    ('NL_RMS257_TAIL1', 1, 257, 'pattern', -32768),
    ('NL_L2_1024_GLOBAL_LAST', 2, 1024, 'pattern', 16384),
    ('NL_L2_1023_TAIL7', 2, 1023, 'pattern', -32768),
    ('NL_L2_513_TAIL1', 2, 513, 'pattern', 32767),
    ('NL_L2_257_TAIL1', 2, 257, 'pattern', -32768),
    ('NL_SOFTMAX1024_EQUAL_U16', 0, 1024, 'zero', 0),
    ('NL_SOFTMAX1023_LAST_NEWMAX', 0, 1023, 'low', 32767),
    ('NL_SOFTMAX513_INTERPOLATE', 0, 513, 'scores', 5120),
    ('NL_SOFTMAX257_CUTOFF', 0, 257, 'cutoff', 0),
    ('NL_RMS1_EXTREME_GAMMA', 1, 1, 'pattern', -32768),
    ('NL_SOFTMAX1_U16', 0, 1, 'zero', 32767),
    ('NL_RMS1024_ZERO_SIGNED_GAMMA', 1, 1024, 'zero', 0),
]


def rne(value, shift):
    if shift == 0:
        return value
    q, r = divmod(value, 1 << shift)
    h = 1 << (shift - 1)
    return q + int(r > h or (r == h and q & 1))


def isqrt(value):
    if value < 2:
        return value
    x = 1 << ((value.bit_length() + 1) // 2)
    while True:
        y = (x + value // x) // 2
        if y >= x:
            return x
        x = y


def clip(value):
    return max(-32768, min(32767, value)), not -32768 <= value <= 32767


def raw(case, index):
    _, _, count, recipe, last = CASES[case]
    if index == count - 1:
        return last
    if recipe == 'zero':
        return 0
    if recipe == 'low':
        return -1024
    if recipe == 'scores':
        return [-4096, -4081, -2048, -1025, -1024, -17, -16, -15][index % 8]
    if recipe == 'cutoff':
        return [-32768, -16385, -16384, -16383, -17, -16, -15, 0][index % 8]
    return PATTERN[index % 8]


def gamma(case, index):
    return -32768 if case == 12 else GAMMA[index % 8]


def pack(values):
    return sum((x & 65535) << (16 * i) for i, x in enumerate(values))


EXP = [round(math.exp(-16 + i / 64) * 32768) for i in range(1025)]


def exp_code(delta):
    if delta < -16384:
        return 0
    if delta >= 0:
        return 32768
    index, fraction = divmod(delta + 16384, 16)
    return EXP[index] + rne((EXP[index + 1] - EXP[index]) * fraction, 4)


def expectation(case):
    name, mode, count, recipe, last = CASES[case]
    values = [raw(case, i) for i in range(count)]
    gains = [gamma(case, i) for i in range(count)]
    saturation = False
    meta = {}
    if mode:
        square = sum(x * x for x in values)
        rad = ((square << 16) // count if mode == 1 else square << 16) + 65536
        root = isqrt(rad)
        factor = (1 << 38) // root
        clipped = [clip(rne(x * factor * g, 30)) for x, g in zip(values, gains)]
        output = [x for x, s in clipped]
        saturation = any(s for x, s in clipped)
        exps = [0] * count
        meta = {'sumsq': square, 'radicand': rad, 'root': root, 'factor': factor}
    else:
        maximum = max(values)
        exps = [exp_code(x - maximum) for x in values]
        factor = (1 << 44) // sum(exps)
        output = [max(0, min(16384, rne(x * factor, 30))) for x in exps]
        meta = {'maximum': maximum, 'exp_sum': sum(exps), 'factor': factor}
    def words(items):
        return [pack(items[i:i + 8]) for i in range(0, count, 8)]
    result = {'name': name, 'mode': mode, 'count': count, 'words': (count + 7) // 8,
              'recipe': recipe, 'last_raw': last, 'epsilon': 1 if mode else 0,
              'saturated': saturation, 'math': meta}
    for key, array in [('output', output), ('exp', exps)]:
        packed = words(array)
        if len(packed) > 1 and any(w != packed[0] for w in packed[:-1]):
            raise AssertionError('periodic compression is not exact')
        result[key + '_common'] = packed[0]
        result[key + '_last'] = packed[-1]
    return result
