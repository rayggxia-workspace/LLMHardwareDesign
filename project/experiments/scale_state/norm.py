"""Integer RMSNorm candidate on frozen full-hidden consumer sums, no model rerun.

Only epsilon/gamma/sqrtH compilation and numerical diagnostics use floating
point. The norm->A8K128->next-projection candidate executes integers. Costs are
explicit unimplemented hardware candidates, not measured target cycles/PPA.
"""
import argparse
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from fractions import Fraction
import json
import math
from pathlib import Path
import platform
import time
import numpy as np
import consumer as C

U64 = (1 << 64)-1


def unsigned64(value):
    value = int(value)
    if not 0 <= value <= U64: raise OverflowError('U64 range')
    return value


def sqrt32(value):
    """32 radix4 restoring steps on an unsigned64 radicand."""
    value = unsigned64(value); root = remainder = 0
    for bit in range(62, -1, -2):
        remainder = (remainder << 2) | ((value >> bit) & 3)
        trial = (root << 2) | 1
        if remainder >= trial: remainder -= trial; root = (root << 1) | 1
        else: root <<= 1
    if root != math.isqrt(value) or remainder != value-root*root: raise AssertionError('independent math.isqrt')
    return root


def divide64(numerator, denominator):
    """64 restoring steps, U64 numerator/U32 divisor, followed by exact RNE."""
    numerator = unsigned64(numerator); denominator = int(denominator)
    if not 0 < denominator < 1 << 32: raise ValueError('positive U32 divisor')
    quotient = remainder = 0
    for bit in range(63, -1, -1):
        remainder = (remainder << 1) | ((numerator >> bit) & 1)
        if remainder >= denominator: remainder -= denominator; quotient |= 1 << bit
    quotient += 2*remainder > denominator or (2*remainder == denominator and quotient % 2)
    if quotient != round(Fraction(numerator, denominator)): raise AssertionError('Fraction inverse divider RNE')
    return unsigned64(quotient)


def compile_constants(raw_gamma, H):
    gamma_float = np.add(np.asarray(raw_gamma, dtype=np.float32), np.float32(1))
    gamma = np.rint(gamma_float.astype(np.float64)*2.**20)
    if not np.isfinite(gamma).all() or gamma.min() < -(1 << 31) or gamma.max() >= 1 << 31: raise OverflowError('S32Q20 gamma')
    for f, q in zip(gamma_float, gamma):
        if round(Fraction(float(f))*2**20) != int(q): raise AssertionError('Fraction offline gamma')
    eps = round(1e-6*2**40); sqrtH = round(math.sqrt(H)*2**20)
    with localcontext() as context:
        context.prec = 60
        if int((Decimal('0.000001')*Decimal(2)**40).to_integral_value(rounding=ROUND_HALF_EVEN)) != eps: raise AssertionError('Decimal epsilon compiler')
        if int((Decimal(H).sqrt()*Decimal(2)**20).to_integral_value(rounding=ROUND_HALF_EVEN)) != sqrtH: raise AssertionError('Decimal sqrtH compiler')
    if not 0 < sqrtH < 1 << 32: raise OverflowError('sqrtH U32Q20')
    return gamma.astype(np.int32), eps, sqrtH


def encode16(sums, units):
    R, H = sums.shape; x = np.empty(sums.shape, dtype=np.int16); exponents = np.empty(R, dtype=np.int16)
    for row in range(R):
        origin = int(np.min(units[row])); aligned = []
        for value, unit in zip(sums[row], units[row]):
            distance = int(unit)-origin
            if distance > 63: raise OverflowError('row alignment shift>63')
            aligned.append(C.checked(int(value) << distance))
        maximum = max(abs(v) for v in aligned)
        if maximum == 0:
            x[row] = 0; exponents[row] = 0
            for value in aligned:
                if round(Fraction(value)*Fraction(2)**origin) != 0: raise AssertionError('Fraction zero X16')
            continue
        shift = maximum.bit_length()-15
        covered = maximum <= 32767*(1 << shift) if shift >= 0 else maximum*(1 << -shift) <= 32767
        if not covered: shift += 1
        exponent = origin+shift
        if not -32768 <= exponent <= 32767: raise OverflowError('row exponent S16')
        exponents[row] = exponent
        for col, value in enumerate(aligned):
            q = C.rne(value, shift)
            if q != round(Fraction(value)*Fraction(2)**(-shift)) or not -32767 <= q <= 32767: raise AssertionError('Fraction X16 encoding')
            x[row, col] = q
    return x, exponents


def integer_norm(sums, units, gamma, eps, sqrtH):
    if sums.dtype != np.int64 or units.dtype != np.int16 or gamma.dtype != np.int32: raise ValueError('sum/unit/gamma dtype')
    if sums.shape != units.shape or len(gamma) != sums.shape[1]: raise ValueError('complete row shape')
    x, e = encode16(sums, units); R, H = x.shape; norm = np.empty(x.shape, dtype=np.int32)
    intermediate = np.empty(x.shape, dtype=np.int32); den = np.zeros(R, dtype=np.uint64)
    roots = np.zeros(R, dtype=np.uint32); inv = np.zeros(R, dtype=np.uint32); squares = np.zeros(R, dtype=np.uint64)
    for row in range(R):
        if not x[row].any():
            norm[row] = 0; intermediate[row] = 0
            for col in range(H):
                if round(Fraction(int(x[row, col]), 1 << 10)) != 0 or round(Fraction(0*int(gamma[col]), 1 << 20)) != 0: raise AssertionError('Fraction zero norm/gamma')
            continue
        Z = int(np.sum(x[row].astype(np.int64)**2, dtype=np.uint64))
        if Z != sum(int(v)**2 for v in x[row]): raise AssertionError('independent full U64 square sum')
        epsilon_term = C.rne(unsigned64(eps*H), 24+2*int(e[row]))
        Den = unsigned64((Z << 16)+epsilon_term)
        if Den == 0: raise ValueError('nonzero row has zero denominator')
        root = sqrt32(Den); inverse = divide64(unsigned64(int(sqrtH) << 18), root)
        if inverse >= 1 << 32: raise OverflowError('inverse U32Q30')
        squares[row] = Z; den[row] = Den; roots[row] = root; inv[row] = inverse
        for col in range(H):
            product = C.checked(int(x[row, col])*inverse)
            normalized = C.checked(C.rne(product, 10), 32)
            if normalized != round(Fraction(int(x[row, col])*inverse, 1 << 10)): raise AssertionError('Fraction pre-gamma norm')
            weighted = C.checked(normalized*int(gamma[col])); value = C.checked(C.rne(weighted, 20), 32)
            if value != round(Fraction(normalized*int(gamma[col]), 1 << 20)): raise AssertionError('Fraction gamma final norm')
            intermediate[row, col] = normalized; norm[row, col] = value
    return {'X16': x, 'row_exponent': e, 'square_sum_U64': squares, 'Den_U64': den, 'sqrt_U32': roots,
            'inv_Q30_U32': inv, 'before_gamma_S32Q20': intermediate, 'norm_S32Q20': norm}


def encode8(source):
    R, H = source.shape
    if source.dtype != np.int32 or H % 128: raise ValueError('S32Q20 norm/K128 format')
    a = np.empty(source.shape, dtype=np.int8); ae = np.empty((R, H//128), dtype=np.int8)
    for row in range(R):
        for g, start in enumerate(range(0, H, 128)):
            unit = C.cover_exponent(np.max(abs(source[row, start:start+128].astype(np.int64))))
            ae[row, g] = unit
            for col in range(start, start+128):
                q = C.rne(source[row, col], unit+20)
                if q != round(Fraction(int(source[row, col]))*Fraction(2)**(-20-unit)) or not -127 <= q <= 127: raise AssertionError('Fraction fresh integer A8')
                a[row, col] = q
    return a, ae


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capture', type=Path, required=True); p.add_argument('--consumer', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True); p.add_argument('--binding', type=Path, required=True); a = p.parse_args()
    if a.out.exists(): raise ValueError('refuse overwrite')
    b = json.loads(a.binding.read_text()); dep = Path(C.__file__)
    if C.sha(__file__) != b['norm_sha256'] or C.sha(dep) != b['consumer_sha256']: raise ValueError('norm/dependency source binding')
    cm, rawfile = C.verify_capture(a.capture); m = json.loads((a.consumer/'manifest.json').read_text())
    if m['status'] != 'PASS' or m['input_manifest_sha256'] != C.sha(a.capture/'manifest.json'): raise ValueError('consumer/capture binding')
    for name, desc in m['artifacts'].items():
        file = (a.consumer/name).resolve()
        if not file.is_relative_to(a.consumer.resolve()) or C.sha(file) != desc['sha256'] or file.stat().st_size != desc['bytes']: raise ValueError('consumer artifact SHA')
    with np.load(rawfile, allow_pickle=False) as raw: raw_gamma = raw['weight.next_norm']; native = {c: raw[c+'.projection'] for c in ('prefill', 'decode')}
    with np.load(a.consumer/'common.npz', allow_pickle=False) as z: w, we, final_base = z['next.W8'], z['next.We'], z['next.Ybase']
    H = len(raw_gamma)
    if H != 2560: raise ValueError('frozen complete hidden2560')
    a.out.mkdir(parents=True); start = time.monotonic()
    try: gamma, eps, sqrtH = compile_constants(raw_gamma, H)
    except (ValueError, OverflowError, AssertionError) as exc:
        C.save(a.out/'manifest.json', {'status': 'FAIL', 'source_commit': b['commit'], 'norm_sha256': C.sha(__file__),
                                     'consumer_dependency_sha256': C.sha(dep), 'error_type': type(exc).__name__, 'error': str(exc), 'parameters_retuned': False})
        raise SystemExit(1)
    C.npz(a.out/'constants.npz', {'gamma_S32Q20': gamma, 'eps_U64Q40': np.array(eps, dtype=np.uint64), 'sqrtH_U32Q20': np.array(sqrtH, dtype=np.uint32)})
    records = []; failed = False
    for case in ('prefill', 'decode'):
        for profile in C.PROFILES:
            name = case+'.'+profile
            try:
                with np.load(a.consumer/(name+'.npz'), allow_pickle=False) as old:
                    sums, units, fp_norm, old_acc, old_unit = (old[k] for k in ('sum_acc64', 'sum_units', 'norm_F32_bridge', 'next.acc', 'next.e0'))
                result = integer_norm(sums, units, gamma, eps, sqrtH)
                a8, ae = encode8(result['norm_S32Q20']); nxt, stats = C.linear(a8, ae, w, we)
                final_units = np.broadcast_to(final_base.astype(np.int16)[None], nxt['acc'].shape)
                codes, fq = C.quant_output(nxt['acc'], nxt['e0'], final_units, 8)
                reencoded = C.physical(result['X16'], result['row_exponent'][:, None])
                fp_on_x16 = C.rms_float(reencoded.astype(np.float32), raw_gamma)
                norm_real = C.physical(result['norm_S32Q20'], -20); value = C.physical(nxt['acc'], nxt['e0'])
                active = int(np.count_nonzero(result['square_sum_U64'])); R = len(sums)
                result.update({'next.'+k: v for k, v in nxt.items()}); result['next.final_ACT8'] = codes; result['next.final_units'] = final_units
                C.npz(a.out/(name+'.npz'), result)
                records.append({'id': name, 'status': 'PASS', 'rows': R, 'hidden': H,
                    'X16_reencoding_vs_input_sum': C.error(reencoded, C.physical(sums, units)),
                    'FPnorm_after_X16_vs_original_FPnorm': C.error(fp_on_x16, fp_norm),
                    'integer_norm_vs_FPnorm_on_X16': C.error(norm_real, fp_on_x16),
                    'integer_norm_vs_original_FPnorm': C.error(norm_real, fp_norm),
                    'next_projection_vs_original_FPnorm_chain': C.error(value, C.physical(old_acc, old_unit)),
                    'next_projection_vs_native': C.error(value, native[case]), 'next_integer': stats, 'final_RQ': fq,
                    'counts': {'X16_Fraction_codes': R*H, 'norm_pre_gamma_Fraction_codes': R*H, 'norm_gamma_Fraction_codes': R*H,
                               'fresh_A8_Fraction_codes': R*H, 'isqrt_math_oracles': active, 'divider_Fraction_oracles': active,
                               'isqrt_restoring_rounds': active*32, 'divide_restoring_rounds': active*64, 'zero_rows': R-active},
                    'candidate_cost': {'gamma_S32Q20_bytes': gamma.nbytes, 'norm_S32Q20_row_bytes': H*4, 'X16_row_bytes': H*2,
                         'mixed_sum_I64_plus_I16_row_bytes': H*10, 'inverse_U32Q30_bytes_per_row': 4,
                         'X16_square_products': active*H, 'U64_square_sum_add_terms': active*H,
                         'S8_only_products_per_S16square_upper': 9, 'S16xU32_products': active*H, 'S32xS32_gamma_products': active*H,
                         'S8_only_products_per_S16xU32_upper': 15, 'S8_only_products_per_S32xS32_upper': 25,
                         'S8_decomposition_scope': 'candidate3x5 or5x5 radix128 S8 products plus S64 shift/add; not executed S8 multiplier kernels or free wide hardware',
                         'sqrt_div_scope': 'actual software32-step radix4 isqrt and64-step U64/U32 restoring divide/RNE; hardware resources/clock/latency uncalibrated',
                         '1RW128bit_row_read_write_lower_bound_beats': {'sum_and_units_read': (H*10+15)//16, 'X16_write_read': 2*((H*2+15)//16),
                              'gamma_read': (H*4+15)//16, 'norm32_write_read': 2*((H*4+15)//16)},
                         'buffer_scope': 'buffers/squares/scan/RNE/metadata share finite ports; no finite schedule or PPA; full gamma plus norm32 row exceeds16KiB'},
                    'fresh_A8_source': 'integer S32Q20, no floating bridge or encode_rows', 'integer_norm_candidate': True,
                    'full_integer_model_qualified': False, 'hardware_performance_accepted': False})
            except (ValueError, OverflowError, AssertionError) as exc:
                failed = True; records.append({'id': name, 'status': 'FAIL', 'error_type': type(exc).__name__, 'error': str(exc), 'parameters_retuned': False})
    C.save(a.out/'norm.json', records)
    C.save(a.out/'manifest.json', {'status': 'FAIL' if failed else 'PASS', 'source_commit': b['commit'], 'norm_sha256': C.sha(__file__), 'consumer_dependency_sha256': C.sha(dep),
        'capture_manifest_sha256': C.sha(a.capture/'manifest.json'), 'consumer_manifest_sha256': C.sha(a.consumer/'manifest.json'),
        'conditions': len(records), 'passed': sum(r['status'] == 'PASS' for r in records), 'epsilon': {'decimal': '0.000001', 'compiled_U64Q40': eps},
        'sqrtH_U32Q20': sqrtH, 'gamma_compile': 'offlineFP32 effective1+stored_weight -> RNE S32Q20, Fraction checked',
        'Den_contract': '(sum(X16^2)<<16)+RNE(epsQ40*H,24+2*eRow); U64 nonzero; zero input row returns0',
        'norm_contract': 'invQ30=RNE((sqrtH_Q20<<18)/isqrt(Den)); normQ20=RNE(X16*invQ30,10); thenRNE(*gammaQ20,20)checkedS32',
        'seconds': time.monotonic()-start, 'environment': {'python': platform.python_version(), 'numpy': np.__version__},
        'scope': __doc__, 'float_runtime_fallback': False, 'whole_integer_model_qualified': False,
        'artifacts': {f.name: {'bytes': f.stat().st_size, 'sha256': C.sha(f)} for f in sorted(a.out.iterdir()) if f.is_file()}})
    print(json.dumps({'status': 'FAIL' if failed else 'PASS', 'conditions': len(records), 'passed': sum(r['status'] == 'PASS' for r in records)}), flush=True)
    if failed: raise SystemExit(1)


if __name__ == '__main__': main()
