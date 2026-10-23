"""C1 integer arithmetic. No floating arithmetic or implicit machine wrap."""
from collections import Counter


def require_int(value):
    if type(value) is not int:
        raise TypeError("Python int required; convert declared integer tensors explicitly")
    return value


def checked(value, bits, signed=True):
    require_int(value)
    low, high = (-(1 << (bits-1)), (1 << (bits-1))-1) if signed else (0, (1 << bits)-1)
    if not low <= value <= high:
        raise OverflowError(f"{value} outside {'i' if signed else 'u'}{bits}")
    return value


def sat(value, bits, counts=None):
    low, high = -(1 << (bits-1)), (1 << (bits-1))-1
    if counts is not None and not low <= value <= high:
        counts["saturation_i"+str(bits)] += 1
    return min(high, max(low, value))


def rne_shift(value, shift):
    require_int(value); require_int(shift)
    if not 0 <= shift <= 63:
        raise ValueError("right shift must be 0..63")
    if shift == 0:
        return value
    magnitude = abs(value)
    quotient = magnitude >> shift
    remainder = magnitude & ((1 << shift)-1)
    half = 1 << (shift-1)
    quotient += remainder > half or (remainder == half and bool(quotient & 1))
    return -quotient if value < 0 else quotient


def mul_radix7(a, b, a_bits, b_bits, counts=None, b_unsigned=False):
    """Fixed-count signed8 partial products plus a candidate 64-bit adder.

    The adder/shift/sign hardware is additional to the 8-bit multiplier. Python
    execution time is unrelated to these target micro-operation counts.
    """
    checked(a,a_bits); checked(b,b_bits,signed=not b_unsigned)
    na, nb = (a_bits+6)//7, (b_bits+6)//7
    aa, bb = abs(a), abs(b)
    result=0
    for i in range(na):
        for j in range(nb):
            # 0..127 is representable by the declared signed8 multiplier.
            product=((aa >> (7*i)) & 127)*((bb >> (7*j)) & 127)
            result += product << (7*(i+j))
    if (a < 0) != (b < 0):
        result=-result
    checked(result,64)
    if counts is not None:
        counts["mul8_partial_products"] += na*nb
        counts[f"wide_mul_{a_bits}x{b_bits}"] += 1
    return result


def mul_i16_i8(a,b,counts=None):
    checked(a,16); checked(b,8)
    result=sum(((abs(a) >> (7*i)) & 127)*b << (7*i) for i in range(3))
    if a < 0:
        result=-result
    if counts is not None:
        counts["mul8_partial_products"] += 3
        counts["wide_mul_16x8"] += 1
    return checked(result,32)


def requant(acc, multiplier, shift, bits=8, counts=None):
    checked(acc,32); checked(multiplier,31,signed=False)
    if bits not in (8,16):
        raise ValueError("candidate output supports i8/i16")
    product=mul_radix7(acc,multiplier,32,31,counts,b_unsigned=True)
    return sat(rne_shift(product,shift),bits,counts)


def udiv_restoring(numerator, denominator, bits, counts=None):
    checked(numerator,bits,False); checked(denominator,bits,False)
    if denominator == 0:
        raise ZeroDivisionError("candidate contract rejects divide by zero")
    quotient=remainder=0
    for bit in range(bits-1,-1,-1):
        remainder=(remainder << 1) | ((numerator >> bit) & 1)
        if remainder >= denominator:
            remainder -= denominator
            quotient |= 1 << bit
    if counts is not None:
        counts[f"udiv{bits}_iterations"] += bits
    return quotient,remainder


def div_rne_unsigned(numerator, denominator, bits=64, counts=None):
    q,r=udiv_restoring(numerator,denominator,bits,counts)
    q += r*2 > denominator or (r*2 == denominator and bool(q & 1))
    return q


def isqrt48(value, counts=None):
    checked(value,48,False)
    root=remainder=0
    for pair in range(23,-1,-1):
        remainder=(remainder << 2) | ((value >> (pair*2)) & 3)
        candidate=(root << 2) | 1
        root <<= 1
        if remainder >= candidate:
            remainder -= candidate
            root |= 1
    if counts is not None:
        counts["isqrt48_iterations"] += 24
    return root


def gemm_i8(a,w):
    """W is [output_channel,K]. Integer reference, not an INT8 speed backend."""
    import numpy as np
    a,w=np.asarray(a),np.asarray(w)
    if a.dtype != np.int8 or w.dtype != np.int8 or a.ndim!=2 or w.ndim!=2 or a.shape[1]!=w.shape[1]:
        raise ValueError("strict i8 [M,K] and [N,K] required")
    k=a.shape[1]
    if k*16384 > (1 << 31)-1:
        raise OverflowError("conservative all-prefix INT32 bound exceeded; not a claimed actual overflow")
    acc=a.astype(np.int64) @ w.astype(np.int64).T
    if np.any(acc < -(1 << 31)) or np.any(acc > (1 << 31)-1):
        raise OverflowError("INT32 overflow")
    return acc.astype(np.int32)
