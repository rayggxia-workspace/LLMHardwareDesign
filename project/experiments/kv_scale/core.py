"""Integer candidates; offline calibration is separate from these arithmetic paths."""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "integer_precision"))
from fixed import checked, rne_shift, sat, mul_radix7, mul_i16_i8, div_rne_unsigned
from vectors import softmax_fixed


def requant_wide(value, multiplier, shift, bits, width, counts):
    checked(value, width)
    checked(multiplier, 31, False)
    if width not in (32, 33) or bits not in (8, 16):
        raise ValueError("RQ32/RQ33 -> i8/i16 only")
    product = mul_radix7(value, multiplier, width, 31, counts, b_unsigned=True)
    return sat(rne_shift(product, shift), bits, counts)


def signed_div_rne(value, denominator, counts):
    checked(value, 64)
    checked(denominator, 64, False)
    result = div_rne_unsigned(abs(value), denominator, 64, counts)
    return -result if value < 0 else result


def pv_block(probabilities, values, counts, probability_bits=15):
    """P<=32767 fits signed16; each 16x8 product costs three 8x8 partials."""
    if (not values or len(probabilities) != len(values) or not values[0]
            or probability_bits not in (7, 15)):
        raise ValueError("nonempty P/V block required")
    dimension = len(values[0])
    if any(len(row) != dimension for row in values):
        raise ValueError("ragged V")
    limit = (1 << probability_bits) - 1
    if len(values) * limit * 128 > (1 << 31) - 1:
        raise OverflowError("conservative all-prefix PV i32 bound exceeded")
    output = [0] * dimension
    for probability, row in zip(probabilities, values):
        if type(probability) is not int or not 0 <= probability <= limit:
            raise ValueError("P must be nonnegative signed16")
        for j, v in enumerate(row):
            checked(v, 8)
            if probability_bits == 7:
                product = probability * v
                counts["mul8_partial_products"] += 1
                counts["pv_native_mul8"] += 1
            else:
                product = mul_i16_i8(probability, v, counts)
            output[j] = checked(output[j] + product, 32)
            counts["pv_i32_adds"] += 1
    return output


def align_pv(partials, exponents, probability_bits, counts, output_fraction=12):
    if (not partials or len(partials) != len(exponents) or probability_bits not in (7, 15)
            or any(len(p) != len(partials[0]) for p in partials)):
        raise ValueError("invalid partials/exponents/P")
    for e in exponents:
        checked(e, 8)
    base = min(exponents)
    if max(exponents) - base > 31:
        raise OverflowError("candidate scale spread limit exceeded")
    numerator = [0] * len(partials[0])
    for partial, exponent in zip(partials, exponents):
        for j, value in enumerate(partial):
            checked(value, 32)
            shifted = checked(value << (exponent - base), 64)
            numerator[j] = checked(numerator[j] + shifted, 64)
            counts["pv_i64_align_adds"] += 1
    shift = base + output_fraction
    denominator = (1 << probability_bits) - 1
    output = []
    for value in numerator:
        if shift >= 0:
            value = checked(value << shift, 64)
            divisor = denominator
        else:
            divisor = checked(denominator << -shift, 64, False)
        output.append(sat(signed_div_rne(value, divisor, counts), 16, counts))
    return output, numerator, base


def integer_attention(q, k, v, k_exponents, v_exponents, score_params, block,
                      probability_bits, allowed, exp_table):
    """Inputs are already quantized lists. No float in dot, score, softmax or PV."""
    if (not q or not k or not v or block <= 0 or len(k) != len(v)
            or len(allowed) != len(q) or len(score_params) != len(q)):
        raise ValueError("invalid nonempty attention")
    blocks = (len(k) + block - 1) // block
    if len(k_exponents) != blocks or len(v_exponents) != blocks:
        raise ValueError("wrong scale block count")
    if len(q[0]) * 16384 > (1 << 31) - 1:
        raise OverflowError("conservative QK i32 bound")
    counts, rows = Counter(), []
    for qi, query in enumerate(q):
        if (len(allowed[qi]) != len(k) or not any(allowed[qi])
                or len(score_params[qi]) != blocks):
            raise ValueError("invalid mask or score scale")
        scores, raw = [], []
        for ti, key in enumerate(k):
            if len(query) != len(key):
                raise ValueError("QK shape")
            acc = 0
            for a, b in zip(query, key):
                checked(a, 8); checked(b, 8)
                acc = checked(acc + a * b, 32)
                counts["qk_mul8"] += 1
                counts["qk_i32_adds"] += 1
            raw.append(acc)
            m, r = score_params[qi][ti // block]
            scores.append(requant_wide(acc, m, r, 16, 32, counts))
        probs, soft = softmax_fixed(scores, exp_table, probability_bits, allowed[qi], counts)
        partials = [pv_block(probs[start:start + block], v[start:start + block], counts, probability_bits)
                    for start in range(0, len(v), block)]
        output, aligned, base = align_pv(partials, v_exponents, probability_bits, counts)
        rows.append({"qk_i32": raw, "scores_i16_f8": scores, "probabilities": probs,
                     "softmax": soft, "partials_i32": partials, "aligned_i64": aligned,
                     "aligned_exponent": base, "output_i16_f12": output})
    return rows, dict(counts)
