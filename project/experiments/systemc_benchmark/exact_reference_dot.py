"""Faster HOST integer oracle; never a hardware recipe or device speedup.

Binary64 BLAS is exact for integer products/reduction whenever the sum of
absolute product bounds is <=2**53. Otherwise split operands into radix-65536
pieces, prove this bound for every partial, and reconstruct in bounded S64.
Unproven cases fall back to NumPy's signed-integer matmul, with an S64 bound.
"""
from collections import Counter
import numpy as np
from contraction_bounds import absolute_contraction_bound


def magnitude(x):
    return max(abs(int(x.min())), abs(int(x.max())))


class ExactReferenceDot:
    def __init__(self):
        self.calls = Counter()

    def dot(self, node, x, y):
        x, y = np.asarray(x), np.asarray(y)
        if (x.size == 0 or y.size == 0 or x.dtype.kind != 'i' or y.dtype.kind != 'i'):
            raise ValueError('nonempty signed integer operands required')
        k = x.shape[-1]
        if k != y.shape[-2 if y.ndim > 1 else -1]:
            raise ValueError('dot dimensions differ')
        bound = magnitude(x) * magnitude(y) * k
        if bound > (1 << 53):
            bound = absolute_contraction_bound(x, y, right_axis=-2 if y.ndim > 1 else -1)
        if bound > (1 << 63) - 1:
            raise ValueError('host oracle lacks a valid S64 absolute-sum bound')

        def exact(a, b):
            estimate = magnitude(a) * magnitude(b) * k
            if estimate > 1 << 53:
                estimate = absolute_contraction_bound(a, b, right_axis=-2 if b.ndim > 1 else -1)
            if estimate > 1 << 53:
                raise ValueError('binary64 exactness proof failed')
            z = np.matmul(a.astype(np.float64), b.astype(np.float64))
            if not np.all(np.isfinite(z)) or not np.all(z == np.rint(z)):
                raise ValueError('BLAS violated integer exactness')
            return z.astype(np.int64)

        if bound <= 1 << 53:
            self.calls['binary64_proven'] += 1
            return exact(x, y)
        if magnitude(x) <= 1 << 31 and magnitude(y) <= 1 << 31:
            xp = (x & 65535, x >> 16)
            yp = (y & 65535, y >> 16)
            partials = [(a, b, 16 * (i + j)) for i, a in enumerate(xp)
                        for j, b in enumerate(yp)]
            partial_bounds = [magnitude(a) * magnitude(b) * k for a, b, _ in partials]
            if (all(v <= 1 << 53 for v in partial_bounds) and
                    sum(v << shift for v, (_, _, shift) in zip(partial_bounds, partials)) <= (1 << 63) - 1):
                result = None
                for a, b, shift in partials:
                    value = exact(a, b) << shift
                    result = value if result is None else result + value
                self.calls['radix16_binary64_proven'] += 1
                return result
        self.calls['integer_fallback'] += 1
        return np.matmul(x, y)
