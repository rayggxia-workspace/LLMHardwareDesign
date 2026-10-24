"""Independent scalar oracle for Issue72, with no producer imports.

Integer runtime references use Python int, Fraction, and bit algorithms.  A
compiler may have used floating point to construct the frozen constants; that
does not turn that compiler into a runtime hardware implementation.
"""
from fractions import Fraction


def need(condition, label):
    if not condition:
        raise ValueError(label)


def integer(value):
    # In particular do not silently truncate a float or accept True as a code.
    need(type(value) is int, "Python integer required")
    return value


def round_rational(numerator, denominator):
    """Nearest/even for any signed rational; independent sign/tie definition."""
    n, d = integer(numerator), integer(denominator)
    need(d > 0, "positive denominator")
    f = Fraction(n, d)
    lo = f.numerator // f.denominator
    distance = f - lo
    if distance < Fraction(1, 2):
        return lo
    if distance > Fraction(1, 2):
        return lo + 1
    return lo if lo % 2 == 0 else lo + 1


def shift_rne(code, shift):
    n, s = integer(code), integer(shift)
    need(-256 <= s <= 256, "bounded shift")
    return round_rational(n, 1 << s) if s >= 0 else n * (1 << -s)


def signed_limits(bits):
    b = integer(bits)
    need(2 <= b <= 256, "signed width")
    return -(1 << (b - 1)), (1 << (b - 1)) - 1


def saturate(code, bits):
    n = integer(code)
    lo, hi = signed_limits(bits)
    return min(hi, max(lo, n)), n < lo or n > hi


def checked(code, bits):
    n = integer(code)
    lo, hi = signed_limits(bits)
    need(lo <= n <= hi, "signed overflow")
    return n


def requant(code, multiplier, shift, bits):
    # The unfused wide product and rounding are distinct specified steps.
    product = integer(code) * integer(multiplier)
    rounded = shift_rne(product, integer(shift))
    out, clipped = saturate(rounded, bits)
    return dict(product=product, rounded=rounded, code=out, saturated=clipped)


def complete_dot(a, w, accumulator_bits=32):
    need(len(a) == len(w) and len(a) > 0, "complete nonempty dot")
    aa, ww = [integer(x) for x in a], [integer(x) for x in w]
    need(all(-127 <= x <= 127 for x in aa + ww), "symmetric S8 domain")
    # Every prefix is checked, not only the final cancellation.
    value = 0
    for x, y in zip(aa, ww):
        value = checked(value + x * y, accumulator_bits)
    return value


def signed_s8_digits(code, bits):
    """Radix-128 low digits and a signed S8 most-significant digit.

    Width fixes the number of digits.  Tiny observed operands therefore do not
    earn a hidden fast path in the conditional service inventory.
    """
    n = checked(integer(code), bits)
    count = 1 if bits <= 8 else 1 + (bits - 8 + 6) // 7
    remainder = n
    result = []
    for _ in range(count - 1):
        result.append(remainder & 127)
        remainder >>= 7
    result.append(remainder)
    need(all(-128 <= v <= 127 for v in result), "true signed S8 digits")
    need(sum(x * (1 << (7 * i)) for i, x in enumerate(result)) == n,
         "digit reconstruction")
    return result


def lowered_product(a, b, a_bits, b_bits, product_bits=128):
    left, right = signed_s8_digits(a, a_bits), signed_s8_digits(b, b_bits)
    value = 0
    partials = []
    for i, x in enumerate(left):
        for j, y in enumerate(right):
            partial = x * y
            shift = 7 * (i + j)
            value = checked(value + (partial << shift), product_bits)
            partials.append(dict(left=i, right=j, product=partial, shift=shift,
                                 accumulated=value))
    need(value == a * b, "S8 digit product reconstruction")
    return dict(value=value, partials=partials, s8_products=len(partials),
                wide_shift_adds=len(partials),
                claim="exact arithmetic lowering; timing/RTL not established")


def unsigned_divmod_bits(numerator, denominator, numerator_bits):
    n, d, width = integer(numerator), integer(denominator), integer(numerator_bits)
    need(1 <= width <= 256 and 0 <= n < 1 << width and d > 0,
         "restoring division domain")
    quotient = remainder = 0
    # One restoring iteration per declared numerator bit; no native // here.
    for bit in range(width - 1, -1, -1):
        remainder = (remainder << 1) | ((n >> bit) & 1)
        quotient <<= 1
        if remainder >= d:
            remainder -= d
            quotient |= 1
    need(quotient * d + remainder == n and 0 <= remainder < d,
         "restoring division identity")
    return quotient, remainder


def divided_rne(numerator, denominator, numerator_bits=128):
    n, d = integer(numerator), integer(denominator)
    need(d > 0, "division denominator")
    q, r = unsigned_divmod_bits(abs(n), d, numerator_bits)
    if 2 * r > d or (2 * r == d and q & 1):
        q += 1
    return -q if n < 0 else q


def isqrt_bits(radicand, radicand_bits=128):
    """Restoring square root, ceil(width/2) fixed digit-pair iterations."""
    n, width = integer(radicand), integer(radicand_bits)
    need(1 <= width <= 256 and 0 <= n < 1 << width, "square-root domain")
    result = remainder = 0
    for pair in range((width + 1) // 2 - 1, -1, -1):
        remainder = (remainder << 2) | ((n >> (2 * pair)) & 3)
        trial = (result << 2) | 1
        result <<= 1
        if remainder >= trial:
            remainder -= trial
            result |= 1
    need(result * result <= n < (result + 1) * (result + 1), "sqrt bracket")
    return result


def lookup(table, index, policy="clamp"):
    need(isinstance(table, (tuple, list)) and len(table) > 0, "integer LUT")
    need(all(type(x) is int for x in table), "LUT contains noninteger data")
    i = integer(index)
    need(policy in ("clamp", "reject"), "LUT boundary policy")
    if policy == "reject":
        need(0 <= i < len(table), "LUT out of range")
    return table[max(0, min(len(table) - 1, i))]


def stable_topk(codes, k):
    values = [integer(x) for x in codes]
    need(type(k) is int and 0 < k <= len(values), "topk domain")
    return sorted(range(len(values)), key=lambda i: (-values[i], i))[:k]
