"""Integer upper bounds for every partial sum of a contraction.

Use a cheap max*max*K bound first. The refinement uses row/column L1 bounds,
never floating-point reductions or an integer matmul that could overflow while
trying to prove itself safe. Bounds need not be tight or identify an output.
"""
import numpy as np


def absolute_contraction_bound(x, y, *, left_axis=-1, right_axis=-2, decomposed=False):
    x, y = np.asarray(x), np.asarray(y)
    if not x.size or not y.size or x.dtype.kind != 'i' or y.dtype.kind != 'i':
        raise ValueError('nonempty signed integer operands required')
    k = x.shape[left_axis]
    if k != y.shape[right_axis]:
        raise ValueError('contraction lengths differ')
    mx = max(abs(int(x.min())), abs(int(x.max())))
    my = max(abs(int(y.min())), abs(int(y.max())))
    if decomposed and max(mx, my) > 1 << 31:
        raise ValueError('native component proof requires S32-or-narrower operands')
    # Signed low16 + signed high16*65536 + low-negative*65536.
    # Their sum of absolute contributions is <= abs(raw)+131072; zero has no
    # contribution. Multiplying these norms bounds all nine component products
    # and thus any partial order of the native accumulator, before final RNE.
    extra = 131072 if decomposed else 0
    nx, ny = (mx+extra if mx else 0), (my+extra if my else 0)
    cheap = nx*ny*k
    if not cheap:
        return 0

    def maximum_l1(values, axis, maximum):
        # Prove the unsigned reduction itself safe before using uint64.
        if maximum*k > (1 << 64)-1 or maximum > (1 << 63)-1:
            return None
        absolute = np.abs(values).astype(np.uint64)
        if extra:
            absolute += (values != 0).astype(np.uint64)*np.uint64(extra)
        return int(np.max(np.sum(absolute, axis=axis, dtype=np.uint64)))

    sx, sy = maximum_l1(x, left_axis, nx), maximum_l1(y, right_axis, ny)
    candidates = [cheap]
    if sx is not None:
        candidates.append(sx*ny)
    if sy is not None:
        candidates.append(nx*sy)
    return min(candidates)
