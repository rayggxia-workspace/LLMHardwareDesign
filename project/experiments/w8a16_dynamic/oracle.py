"""Exact dynamic S32 dot contract; no implementation/RTL imports.

The old primitive Dot rounds once after full K.  Fifteen signed A16/W8
partial dots are an exact decomposition, not fifteen independent Q16 dots.
"""
import argparse
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import random

S32_MIN, S32_MAX = -(1 << 31), (1 << 31) - 1
A_SHIFTS, B_SHIFTS = (0, 15, 30), (0, 7, 14, 21, 28)
MAX_K, ACC_BITS = 65535, 80


def a_digits(value):
    assert S32_MIN <= value <= S32_MAX
    answer = (value & 32767, (value >> 15) & 32767, value >> 30)
    assert all(-32768 <= x <= 32767 for x in answer)
    assert sum(x << s for x, s in zip(answer, A_SHIFTS)) == value
    return answer


def b_digits(value):
    assert S32_MIN <= value <= S32_MAX
    answer = tuple((value >> s) & 127 for s in B_SHIFTS[:-1]) + (value >> 28,)
    assert all(-128 <= x <= 127 for x in answer)
    assert sum(x << s for x, s in zip(answer, B_SHIFTS)) == value
    return answer


def finish(value, shift):
    assert 0 <= shift <= 63
    # Fraction is independent of the RTL's arithmetic-right-shift/tie logic.
    rounded = round(Fraction(value, 1 << shift))
    return min(S32_MAX, max(S32_MIN, rounded))


def partials(a, b):
    """K128 then A digit then W digit; each packet has eight raw S32 lanes."""
    assert 1 <= len(a) <= MAX_K and len(b) == len(a)
    n = len(b[0]); assert 1 <= n <= 8 and all(len(x) == n for x in b)
    for kk in range(0, len(a), 128):
        length = min(128, len(a) - kk)
        aa = [a_digits(x) for x in a[kk:kk + length]]
        bb = [[b_digits(y) for y in row] for row in b[kk:kk + length]]
        for ai in range(3):
            for bi in range(5):
                raw = [sum(aa[k][ai] * bb[k][j][bi] for k in range(length)) for j in range(n)]
                assert all(S32_MIN <= x <= S32_MAX for x in raw)
                # 1.0 FP16: mantissa=1024, exponent=-10, Ashift=0.
                # All integers have zero remainder, including negative values.
                assert all(round(Fraction(x * 1024, 1024)) == x for x in raw)
                yield dict(kk=kk, length=length, ai=ai, bi=bi,
                           shift=A_SHIFTS[ai] + B_SHIFTS[bi], raw=raw)


def check(a, b, shift):
    direct = [sum(x * row[j] for x, row in zip(a, b)) for j in range(len(b[0]))]
    merged = [0] * len(b[0]); packets = 0; peak = 0
    for packet in partials(a, b):
        for j, raw in enumerate(packet['raw']):
            merged[j] += raw << packet['shift']
            assert -(1 << (ACC_BITS - 1)) <= merged[j] < (1 << (ACC_BITS - 1))
            peak = max(peak, abs(merged[j]))
        packets += 1
    assert merged == direct
    result = [finish(x, shift) for x in merged]
    assert result == [finish(x, shift) for x in direct]
    return dict(result=result, packets=packets, peak_absolute_prefix=peak)


def run(seed):
    rng = random.Random(seed)
    edges = [S32_MIN, S32_MIN + 1, -1073741825, -32769, -1, 0, 1,
             127, 128, 32767, 32768, 1073741823, S32_MAX]
    for x in edges + [rng.randrange(S32_MIN, S32_MAX + 1) for _ in range(4096)]:
        a_digits(x); b_digits(x)
    # Triangle bound applies to *every* partial ordering, not just final sums.
    a_absolute = 32767 + (32767 << 15) + (2 << 30)
    b_absolute = 127 * sum(1 << s for s in B_SHIFTS[:-1]) + (8 << 28)
    bound = MAX_K * a_absolute * b_absolute
    assert bound < 1 << 79
    assert 128 * 32767 * 127 < 1 << 31
    assert 128 * 32768 * 128 < 1 << 31  # actual signed-port all-prefix bound
    digest = hashlib.sha256(); cases = 0; max_prefix = 0
    lengths = [1, 2, 16, 127, 128, 129, 512] + [rng.randrange(1, 513) for _ in range(24)]
    for case, k in enumerate(lengths):
        n = 1 + case % 8
        a = [rng.choice(edges) if i % 3 == 0 else rng.randrange(S32_MIN, S32_MAX + 1) for i in range(k)]
        b = [[rng.choice(edges) if (i + j) % 3 == 0 else rng.randrange(S32_MIN, S32_MAX + 1)
              for j in range(n)] for i in range(k)]
        a[0] = S32_MIN; b[0][0] = S32_MIN
        for shift in (0, 1, 16, 31, 47, 63):
            evidence = check(a, b, shift)
            max_prefix = max(max_prefix, evidence['peak_absolute_prefix'])
            digest.update(json.dumps([k, n, shift, evidence], sort_keys=True).encode()); cases += 1
    # Maximum admitted full K, positive sum exceeds S64; no intermediate RNE.
    evidence = check([S32_MIN] * MAX_K, [[S32_MIN]] * MAX_K, 63)
    assert evidence['peak_absolute_prefix'] > (1 << 63)
    # A counterexample rejects the tempting per-K128 RNE/prefix variant.
    assert finish(1 + 1, 1) == 1 and finish(1, 1) + finish(1, 1) == 0
    return dict(passed=True, seed=seed, cases=cases + 1, digest=digest.hexdigest(),
                lanes=8, transient_accumulator_bits=80, transient_accumulator_bytes=80,
                max_K=MAX_K, absolute_all_prefix_bound=bound, maximum_observed_prefix=max_prefix,
                partials_per_K128=15, A_signed_bits=16, W_signed_bits=8,
                final_policy='one full-K RNE then S32 saturation',
                raw_scale_one_exact=True, whole_model_numeric_qualified=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--seed', type=int, default=25001)
    parser.add_argument('--out', type=Path, required=True); args = parser.parse_args()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(run(args.seed), indent=2) + '\n', encoding='utf-8')
