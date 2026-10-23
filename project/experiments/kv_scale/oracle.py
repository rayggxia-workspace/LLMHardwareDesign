"""Separate Fraction oracle. Does not import target fixed/core/vectors operations."""
from fractions import Fraction


def dyadic(exponent):
    return Fraction(2 ** exponent) if exponent >= 0 else Fraction(1, 2 ** -exponent)


def clamp(value, bits):
    return max(-(2 ** (bits - 1)), min(2 ** (bits - 1) - 1, value))


def attention(q, k, v, v_exponents, score_params, block, pbits, allowed, table):
    result = []
    scale = 2 ** pbits - 1
    for row, query in enumerate(q):
        raw = [sum(int(a) * int(b) for a, b in zip(query, key)) for key in k]
        scores = [clamp(round(Fraction(value * score_params[row][t // block][0],
                                      2 ** score_params[row][t // block][1])), 16)
                  for t, value in enumerate(raw)]
        peak = max(s for s, ok in zip(scores, allowed[row]) if ok)
        exp = [table[peak - s] if ok and peak - s <= 4096 else 0
               for s, ok in zip(scores, allowed[row])]
        p = [round(Fraction(x * scale, sum(exp))) for x in exp]
        out = [clamp(round(sum(Fraction(p[t] * int(v[t][d]), scale)
                              * dyadic(v_exponents[t // block]) for t in range(len(v)))
                           * 4096), 16) for d in range(len(v[0]))]
        result.append({"qk_i32": raw, "scores_i16_f8": scores,
                       "probabilities": p, "output_i16_f12": out})
    return result
