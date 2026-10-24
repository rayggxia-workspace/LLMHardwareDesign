"""Bounded integer softmax candidates on Issue61 captured, complete GQA groups.

Capture FP32 -> S32Q20 and offline KV/scaling/LUT compilers remain float bridges.
After that boundary QK, score conversion, LUT softmax, P15 and PV are integers.
NumPy integer execution is a reference, not a target kernel, throughput or PPA.
"""
import argparse
from fractions import Fraction
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import platform
import subprocess
import time
import zipfile

import numpy as np


HERE = Path(__file__).resolve().parent
BOUNDS = HERE.parent / 'server_models' / 'bounds.py'
_spec = importlib.util.spec_from_file_location('issue64_pv_bounds', BOUNDS)
_bounds = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_bounds)
pv32 = _bounds.pv32
MODELS = [('gemma', 'gemma-capture01', 'google/gemma-3-4b-it'),
          ('qwen25', 'qwen25-gqa01', 'Qwen/Qwen2.5-3B'),
          ('qwen35', 'qwen35-gqa01', 'Qwen/Qwen3.5-4B')]
GRIDS = (128, 256)
I32_MIN, I32_MAX = -(1 << 31), (1 << 31) - 1
U64_MAX = (1 << 64) - 1


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 << 20), b''):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False) + '\n', newline='\n')


def npz(path, arrays):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for key, value in sorted(arrays.items()):
            data = io.BytesIO()
            np.save(data, np.asarray(value), allow_pickle=False)
            entry = zipfile.ZipInfo(key + '.npy', (2026, 10, 24, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(entry, data.getvalue())


def rne(value, shift):
    """Signed shift, exact nearest-even, with no NumPy wraparound."""
    value, shift = int(value), int(shift)
    if not -63 <= shift <= 63:
        raise ValueError('shift outside declared [-63,63] domain')
    if shift <= 0:
        return value << -shift
    q, rem = divmod(abs(value), 1 << shift)
    half = 1 << (shift - 1)
    q += rem > half or (rem == half and q & 1)
    return -q if value < 0 else q


def fraction_rne(value):
    """Independent scalar Fraction witness for the probability divider."""
    sign = -1 if value < 0 else 1
    value = abs(value)
    whole, remainder = divmod(value.numerator, value.denominator)
    if remainder * 2 > value.denominator or (remainder * 2 == value.denominator and whole % 2):
        whole += 1
    return sign * whole


def bridge(value):
    # Explicit offline float bridge, separate from the integer candidate path.
    source = np.asarray(value, dtype=np.float64)
    rounded = np.rint(source * 2.**20)
    if not np.isfinite(rounded).all() or rounded.min() < I32_MIN or rounded.max() > I32_MAX:
        raise OverflowError('FP32 -> S32Q20 bridge')
    return rounded.astype(np.int32)


def exponent(source):
    maximum = int(np.max(abs(np.asarray(source, dtype=np.int64))))
    shift = max(0, maximum.bit_length() - 7)
    if maximum > 127 << shift:
        shift += 1
    result = shift - 20
    if not -128 <= result <= 127:
        raise OverflowError('i8 exponent')
    return result


def fixed(source, bits, unit):
    bound = (1 << (bits - 1)) - 1
    x = bridge(source)
    codes = np.fromiter((rne(v, int(unit) + 20) for v in x.flat), dtype=np.int64).reshape(x.shape)
    clipped = int(np.count_nonzero(abs(codes) > bound))
    return np.clip(codes, -bound, bound).astype(np.int8 if bits == 8 else np.int16), clipped


def query(source):
    src = bridge(source)
    codes = np.empty(src.shape, dtype=np.int8)
    units = np.empty(src.shape[:-1], dtype=np.int8)
    for index in np.ndindex(units.shape):
        unit = exponent(src[index])
        units[index] = unit
        values = [rne(v, unit + 20) for v in src[index]]
        if any(not -127 <= v <= 127 for v in values):
            raise AssertionError('dynamic query scale failed to cover source')
        codes[index] = values
    return codes, units


def calibrated_exponent(source, bound):
    maximum = float(np.max(abs(np.asarray(source, dtype=np.float64))))
    if not math.isfinite(maximum):
        raise ValueError('finite calibration required')
    # A zero calibration tensor has a declared deterministic unit, not log(0).
    return -20 if maximum == 0 else int(math.ceil(math.log2(maximum / bound)))


def limbs16(source):
    rest = np.asarray(source, dtype=np.int64)
    if np.any(abs(rest) > 32767):
        raise ValueError('symmetric signed16 domain')
    digits = []
    for _ in range(3):
        digit = (rest + 64) % 128 - 64
        digits.append(digit.astype(np.int8))
        rest = (rest - digit) // 128
    if np.any(rest):
        raise AssertionError('radix128 decomposition')
    return digits


def qk32(q, k, kvbits):
    """Actual I32 dot/add over S8 limbs, checked by a full I64 oracle."""
    q, k = np.asarray(q), np.asarray(k)
    if q.ndim != 3 or k.ndim != 2 or q.shape[-1] != k.shape[-1] or q.shape[-1] == 0:
        raise ValueError('Q/K shape')
    if kvbits not in (8, 16) or np.any(abs(q.astype(np.int64)) > 127):
        raise ValueError('Q/K format')
    bound = (1 << (kvbits - 1)) - 1
    if np.any(abs(k.astype(np.int64)) > bound):
        raise ValueError('K format')
    digits = limbs16(k) if kvbits == 16 else [k.astype(np.int8)]
    if q.shape[-1] * 127 * (41024 if kvbits == 16 else 127) > I32_MAX:
        raise OverflowError('QK limb-prefix format bound')
    acc = np.zeros((*q.shape[:-1], len(k)), dtype=np.int32)
    maximum = 0
    for j, digit in enumerate(digits):
        partial = q.astype(np.int32) @ digit.astype(np.int32).T
        term = partial.astype(np.int64) << (7 * j)
        expected = acc.astype(np.int64) + term
        if term.min() < I32_MIN or term.max() > I32_MAX or expected.min() < I32_MIN or expected.max() > I32_MAX:
            raise OverflowError('QK I32 shift/add')
        acc = np.add(acc, term.astype(np.int32), dtype=np.int32)
        if not np.array_equal(acc, expected):
            raise AssertionError('QK I32 prefix sidecar')
        maximum = max(maximum, int(np.max(abs(expected))))
    oracle = q.astype(np.int64) @ k.astype(np.int64).T
    if not np.array_equal(acc, oracle):
        raise AssertionError('QK I64 oracle')
    return acc, {'S8_dot_passes': len(digits), 'full_QK_i32_values': int(acc.size),
                 'max_limb_prefix_abs': maximum, 'INT64_oracle_bitexact': True}


def compile_scale(value):
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError('positive finite scaling required')
    multiplier = round(value * 2**30)
    if not 0 < multiplier < 2**32:
        raise OverflowError('offline U32Q30 score multiplier')
    return multiplier, {'format': 'U32Q30', 'multiplier': multiplier,
                        'source_float_hex': value.hex(), 'absolute_error': abs(multiplier * 2.**-30 - value),
                        'compiler': 'offline FP64 nearest-even; no runtime float scaling'}


def score_q12(dot, qunits, kunit, multiplier):
    if not 0 < int(multiplier) < 2**32:
        raise ValueError('U32Q30 multiplier')
    dot = np.asarray(dot)
    if dot.shape[:-1] != np.asarray(qunits).shape:
        raise ValueError('query scale shape')
    score = np.empty(dot.shape, dtype=np.int32)
    max_product = 0
    for index in np.ndindex(dot.shape[:-1]):
        shift = 30 - int(qunits[index]) - int(kunit) - 12
        for j, value in enumerate(dot[index]):
            product = int(value) * int(multiplier)
            if not -(1 << 63) <= product < (1 << 63):
                raise OverflowError('signed64 score multiplication')
            converted = rne(product, shift)
            if not I32_MIN <= converted <= I32_MAX:
                raise OverflowError('S32Q12 score')
            score[index + (j,)] = converted
            max_product = max(max_product, abs(product))
    return score, {'format': 'S32Q12', 'multiplier_product_format': 'S64',
                   'maximum_abs_S64_product': max_product, 'multiplications_32x32_to64': int(dot.size),
                   'RNE_shift_conversions': int(dot.size),
                   'candidate_cost': '32x32->64 signed-by-unsigned multiply, variable signed RNE shift and S32 range guard; not free S8 hardware'}


def compile_lut(grid):
    if grid not in GRIDS:
        raise ValueError('frozen LUT grids are128/256')
    # Offline compiler only. Index0 is exp(0); the last entry is exp(-16).
    return np.array([round(math.exp(-i / grid) * 2**30) for i in range(16 * grid + 1)], dtype='<u4')


def divide_rne_u64(numerator, denominator):
    numerator = np.asarray(numerator)
    denominator = np.asarray(denominator)
    if numerator.dtype != np.dtype('uint64') or denominator.dtype != np.dtype('uint64'):
        raise TypeError('explicit U64 numerator/denominator required')
    if np.any(denominator == 0):
        raise ZeroDivisionError('softmax sum')
    quotient, rem = np.divmod(numerator, denominator)
    half = denominator // np.uint64(2)
    above = rem > half
    tie = ((denominator & np.uint64(1)) == 0) & (rem == half)
    increment = above | (tie & ((quotient & np.uint64(1)) != 0))
    if np.any(increment & (quotient == np.uint64(U64_MAX))):
        raise OverflowError('U64 rounded division')
    return quotient + increment.astype(np.uint64)


def softmax_integer(scores, mask, grid, lut):
    scores = np.asarray(scores)
    mask = np.asarray(mask, dtype=bool)
    if scores.ndim != 3 or mask.shape != scores.shape[1:] or scores.dtype != np.dtype('int32'):
        raise ValueError('score/mask format or shape')
    if np.any(mask.sum(-1) == 0):
        raise ValueError('fully masked row is not a legal attention query')
    if grid not in GRIDS or np.asarray(lut).shape != (16 * grid + 1,) or lut.dtype != np.dtype('uint32'):
        raise ValueError('LUT format/extent')
    if lut[0] != 1 << 30 or np.any(lut[1:] > lut[:-1]) or np.any(lut == 0):
        raise ValueError('positive monotonic U32Q30 LUT with exact maximum required')
    maximum = np.where(mask[None], scores, I32_MIN).max(-1)
    delta = scores.astype(np.int64) - maximum[:, :, None].astype(np.int64)
    eligible = mask[None] & (delta >= -16 * 4096)
    # Nonnegative index rounding is exact RNE at step32/16 S32Q12 units.
    mag = -np.minimum(delta, 0)
    shift = 5 if grid == 128 else 4
    index = mag >> shift
    rem = mag & ((1 << shift) - 1)
    index += (rem > (1 << (shift - 1))) | ((rem == (1 << (shift - 1))) & ((index & 1) != 0))
    index = np.clip(index, 0, 16 * grid)
    exponents = np.where(eligible, lut[index], 0).astype(np.uint32)
    if scores.shape[-1] * (1 << 30) > U64_MAX:
        raise OverflowError('exp U64 sum format bound')
    sums = exponents.sum(-1, dtype=np.uint64)
    if np.any(sums < 1 << 30):
        raise AssertionError('every nonempty masked row retains an exact maximum exp')
    numerator = exponents.astype(np.uint64) << np.uint64(15)
    p = np.minimum(divide_rne_u64(numerator, sums[:, :, None]), 32767).astype(np.int16)
    if np.any(p[:, ~mask]):
        raise AssertionError('masked probability is nonzero')
    active = mask.sum(-1)
    budget = 32768 + (active + 1) // 2 + 1
    if int(active.max()) * 32767 > (1 << 32) - 1:
        raise OverflowError('declared U32 P-sum counter capacity')
    psum = p.sum(-1, dtype=np.uint32)
    if np.any(psum > budget[None]):
        raise AssertionError('normalized integer P-sum invariant')
    witnesses = 0
    for h, row in np.ndindex(sums.shape):
        # Scalar Fraction checks include the maximum and fixed boundary/interior positions.
        selected = sorted({0, scores.shape[-1] // 2, scores.shape[-1] - 1,
                           int(np.argmax(np.where(mask[row], scores[h, row], I32_MIN)))})
        for j in selected:
            wanted = min(32767, fraction_rne(Fraction(int(exponents[h, row, j]) << 15, int(sums[h, row]))))
            if wanted != int(p[h, row, j]):
                raise AssertionError('Fraction probability RNE witness')
            witnesses += 1
    stats = {'maximum_exp_sum_U64': int(sums.max()), 'maximum_P_sum_U32': int(psum.max()),
             'maximum_P_sum_budget': int(budget.max()), 'masked_nonzero_count': 0,
             'truncated_active_exp_count': int(np.count_nonzero(mask[None] & ~eligible)),
             'Fraction_probability_RNE_witnesses': witnesses,
             'LUT_reads': int(np.count_nonzero(eligible)), 'U64_sum_terms': int(exponents.size),
             'U64_divisions_RNE': int(exponents.size), 'U32_Psum_add_terms': int(p.size),
             'P15_saturation_at32768_count': int(np.count_nonzero(numerator // sums[:, :, None] >= 32768)),
             'runtime_float_fallback': False,
             'Psum_contract': 'U32 counter, normalized P15, budget32768+ceil(active_keys/2)+1, immutable per-head Vscale'}
    return p, exponents, sums, budget, stats


def metric(value, reference):
    reference = np.asarray(reference, dtype=np.float64)
    delta = np.asarray(value, dtype=np.float64) - reference
    return {'relative_rmse': float(np.linalg.norm(delta) / max(np.linalg.norm(reference), 1e-30)),
            'max_abs': float(np.max(abs(delta)))}


def evaluate(q, k, v, ref, cal_k, cal_v, positions, window, scaling, kvbits, grid, lut):
    mask = np.arange(len(k))[None] <= positions[:, None]
    if window:
        mask &= np.arange(len(k))[None] > positions[:, None] - window
    qa, qe = query(q)
    bound = (1 << (kvbits - 1)) - 1
    # These compilers read calibration only, exactly matching the Issue61 rule.
    ke = calibrated_exponent(cal_k, bound)
    ve = calibrated_exponent(cal_v, bound)
    if not -128 <= ke <= 127 or not -128 <= ve <= 127:
        raise OverflowError('KV exponent format')
    ki, kclip = fixed(k, kvbits, ke)
    vi, vclip = fixed(v, kvbits, ve)
    dot, qk_stats = qk32(qa, ki, kvbits)
    multiplier, scale_stats = compile_scale(scaling)
    scores, score_stats = score_q12(dot, qe, ke, multiplier)
    p, exp_codes, exp_sums, budget, sm_stats = softmax_integer(scores, mask, grid, lut)
    output, pv_stats = pv32(p, vi, 16, kvbits, budget)
    independent_pv = p.astype(np.int64) @ vi.astype(np.int64)
    if not np.array_equal(output, independent_pv):
        raise AssertionError('complete PV32 differs from I64 oracle')
    # Float64 same-coded-input oracle is a diagnostic, outside candidate execution.
    exact_scores = dot.astype(np.float64) * np.exp2(qe.astype(np.float64) + ke)[:, :, None] * scaling
    exact_scores = np.where(mask[None], exact_scores, -np.inf)
    exact_scores -= exact_scores.max(-1, keepdims=True)
    probability = np.exp(exact_scores)
    probability /= probability.sum(-1, keepdims=True)
    float_p = np.clip(np.rint(probability * 32768), 0, 32767).astype(np.int16)
    float_out = (float_p.astype(np.int64) @ vi.astype(np.int64)).astype(np.float64) * 2.**(ve - 15)
    converted = output.astype(np.float64) * 2.**(ve - 15)
    native_error = metric(converted, ref)
    exact_unmasked_scores = dot.astype(np.float64) * np.exp2(qe.astype(np.float64) + ke)[:, :, None] * scaling
    score_error = abs(scores.astype(np.float64) * 2.**-12 - exact_unmasked_scores)
    rows = int(np.prod(q.shape[:2]))
    score_bytes = int(scores.nbytes)
    exp_bytes = int(exp_codes.nbytes)
    p_bytes = int(p.nbytes)
    multiplier_digits = [(multiplier >> (7*j)) & 127 for j in range(5)]
    dyadic = (multiplier & (multiplier-1)) == 0
    score_stats.update(
        offline_constant_nonnegative_radix128_digits=multiplier_digits,
        S8_only_alternative_products_per_score=0 if dyadic else 5 * sum(d != 0 for d in multiplier_digits),
        S8_only_alternative_note=('constant power-of-two multiplier may merge into the one RNE shift, bitexact with checked range'
                                 if dyadic else 'five balanced S8 digits for signed32 input times nonzero unsigned7 constant digits; requires wide shift/add/reduction, not executed or free'),
        actual_reference='checked software signed64 product and RNE; neither a measured multiplier nor its S8 decomposition kernel')
    operations = {'QK': qk_stats, 'score': score_stats, 'softmax': sm_stats, 'PV': pv_stats,
                  'not_timed': True, 'matrix_resources': 'one shared S8 candidate; QK and PV cannot be credited as simultaneous independent arrays',
                  'non_S8_resources_required': 'signed32xunsigned32->S64 score multiplier; S64 RNE shift; U64 sum; U64 numerator shift; U64 divisor/RNE or an equivalent independently validated implementation',
                  'U64_division_candidate': 'restoring divider up to64 iterations/quotient at one bit per iteration, plus compare/subtract/remainder RNE; a candidate implementation cost, no RTL/latency claim'}
    storage = {'Q8_bytes': int(qa.nbytes), 'KV_payload_bytes': int(ki.nbytes + vi.nbytes),
               'KV_calibrated_exponent_bytes': 2, 'Q_exponent_bytes': int(qe.nbytes),
               'score_scaling_U32Q30_bytes': 4, 'LUT_U32Q30_bytes': int(lut.nbytes),
               'score_S32Q12_bytes': score_bytes, 'exp_U32Q30_bytes_if_materialized': exp_bytes,
               'P15_bytes_if_materialized': p_bytes, 'row_max_S32_bytes': rows * 4,
               'row_sum_U64_bytes': rows * 8, 'Psum_guard_U32_bytes': rows * 4,
               'PV_I32_output_bytes': int(output.nbytes),
               'recompute_exp_schedule': {'score_RW_logical_bytes': score_bytes * 3,
                                           'LUT_read_bytes': sm_stats['LUT_reads'] * 8,
                                           'exp_materialization_RW_bytes': 0},
               'materialize_exp_schedule': {'score_RW_logical_bytes': score_bytes * 2,
                                             'LUT_read_bytes': sm_stats['LUT_reads'] * 4,
                                             'exp_materialization_RW_bytes': exp_bytes * 2},
               'LUT_read_bytes_at_one_read_per_eligible_element': sm_stats['LUT_reads'] * 4,
               'schedule_caveat': 'recompute and materialize schedules are alternative same-function costs, never added together; max update streams with the first score write; P15 transport/read/write must be charged separately',
               'port_caveat': 'one1RW bank serializes reads/writes; LUT has one read port unless a separately charged inventory supplies more; payload/header/padding not converted to cycles here',
               'storage_caveat': 'sizes describe full selected-query evidence; tile/live-range scheduling and capacity checks must be supplied by the service experiment; buffers not assumed free'}
    report = {'KV_bits': kvbits, 'P_bits': 16, 'LUT_grid': grid, 'K_exponent': ke, 'V_exponent': ve,
              'K_clips': kclip, 'V_clips': vclip, 'score_scale': scale_stats,
              'integer_output_vs_native': native_error,
              'FP64_same_encoded_KV_P15_output_vs_native': metric(float_out, ref),
              'integer_output_vs_FP64_same_encoded_KV_P15': metric(converted, float_out),
              'P15_code_mismatches_vs_FP64_softmax': int(np.count_nonzero(p != float_p)),
              'score_q12_vs_exact_score_max_abs': float(np.max(score_error[np.broadcast_to(mask, score_error.shape)])),
              'operations': operations, 'storage_and_ports': storage,
              'exploratory_local_RMSE_screen_passed': native_error['relative_rmse'] <= .05 and kclip == 0 and vclip == 0,
              'screen_scope': 'inherited5% local diagnostic only; not a full-model quality criterion',
              'numerical_failure_retained': native_error['relative_rmse'] > .05 or kclip != 0 or vclip != 0,
              'full_model_quality_accepted': False,
              'hardware_supported': False}
    arrays = {'Q8': qa, 'Qe': qe, 'K': ki, 'V': vi, 'QK32': dot, 'scoreQ12': scores,
              'mask': mask, 'positions': positions, 'expQ30': exp_codes, 'exp_sum_U64': exp_sums,
              'P15': p, 'P15_FP64_softmax_reference': float_p, 'Psum_budget': budget,
              'PV32': output, 'native_reference': ref, 'PV_FP64_softmax_reference': float_out}
    return report, arrays


def source_binding(binding_path):
    binding = json.loads(binding_path.read_text()) if binding_path else {}
    files = {'attention.py': Path(__file__), 'server_models/bounds.py': BOUNDS}
    for key, path in files.items():
        field = 'attention_sha256' if key == 'attention.py' else 'bounds_sha256'
        wanted = binding.get(field)
        if wanted is None:
            wanted = next((v for k, v in binding.get('sources', {}).items()
                           if k.replace('\\', '/') == key or k.replace('\\', '/').endswith('/'+key)), None)
        if wanted and sha(path) != wanted:
            raise ValueError('source binding mismatch: ' + key)
    try:
        commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=HERE, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = binding.get('commit', 'unverified: no Git metadata or binding commit')
    if binding.get('commit') and commit != binding['commit']:
        raise ValueError('commit binding mismatch')
    return {'commit': commit, 'files': {key: sha(path) for key, path in files.items()},
            'binding_sha256': sha(binding_path) if binding_path else None,
            'binding_supplied': binding_path is not None}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--binding', type=Path)
    a = p.parse_args()
    if a.out.exists():
        raise ValueError('refuse existing output directory')
    source = source_binding(a.binding)
    a.out.mkdir(parents=True)
    start = time.monotonic()
    tables = {grid: compile_lut(grid) for grid in GRIDS}
    lut_meta = {}
    for grid, lut in tables.items():
        path = a.out / ('exp-grid' + str(grid) + '.u32le.bin')
        path.write_bytes(lut.tobytes())
        lut_meta[str(grid)] = {'entries': len(lut), 'bytes': int(lut.nbytes), 'sha256': sha(path),
                               'domain': 'exp[-16,0], nearest grid with RNE; delta<-16 maps to0',
                               'format': 'U32Q30 little-endian; offline math.exp, runtime ROM lookup'}
    records, inputs = [], {}
    fatal = False
    for name, folder, model_id in MODELS:
        cap = a.root / folder
        manifest = json.loads((cap / 'manifest.json').read_text())
        if manifest.get('sealed_reserved') or 'Phi' in manifest['model']['id']:
            raise ValueError('reserved Phi input is forbidden')
        if manifest['model']['id'] != model_id or manifest['status'] != 'PASS':
            raise ValueError('unaccepted or unexpected model capture')
        checked = {}
        for filename, desc in manifest['artifacts'].items():
            path = (cap / filename).resolve()
            if not path.is_relative_to(cap.resolve()):
                raise ValueError('capture artifact escaped root')
            if sha(path) != desc['sha256'] or path.stat().st_size != desc['bytes']:
                raise ValueError('capture artifact mismatch: ' + filename)
            checked[filename] = {'bytes': path.stat().st_size, 'sha256': desc['sha256']}
        inputs[name] = {'manifest_sha256': sha(cap / 'manifest.json'), 'model': manifest['model'],
                        'artifacts': checked}
        with np.load(cap / 'selected-raw.npz', allow_pickle=False) as z:
            for case in manifest['cases']:
                if case['name'] == 'calibration':
                    continue
                prefix = case['prefix']
                for layer in manifest['selected_layers']:
                    base = case['name'] + '.layer' + str(layer) + '.full.'
                    cal = 'calibration.layer' + str(layer) + '.full.'
                    q, k, v, ref = (z[base + key] for key in ('q', 'k', 'v', 'reference'))
                    positions = np.unique(np.r_[np.arange(min(4, prefix)), np.arange(max(0, prefix - 4), prefix), np.arange(prefix, q.shape[1])])
                    event = next(e for e in case['full_events'] if e['layer'] == layer)
                    if event.get('softcap') is not None:
                        raise ValueError('softcap is outside the frozen candidate')
                    for kvbits in (8, 16):
                        for grid in GRIDS:
                            label = name + '.' + case['name'] + '.l' + str(layer) + '.kv' + str(kvbits) + '.lut' + str(grid)
                            record = {'id': label, 'model': name, 'case': case['name'], 'layer': layer,
                                      'positions': positions.tolist(), 'GQA_Q_heads': len(q), 'head_dim': q.shape[-1],
                                      'keys': len(k), 'window': event['window'], 'KV_bits': kvbits, 'LUT_grid': grid}
                            try:
                                result, arrays = evaluate(q[:, positions], k, v, ref[:, positions], z[cal + 'k'], z[cal + 'v'],
                                                          positions, event['window'], event['scaling'], kvbits, grid, tables[grid])
                                record.update(result, status='PASS')
                                npz(a.out / (label + '.npz'), arrays)
                            except (OverflowError, AssertionError, ValueError, ZeroDivisionError) as exc:
                                fatal = True
                                record.update(status='FAIL', error_type=type(exc).__name__, error=str(exc), numerical_failure_retained=True)
                            records.append(record)
    save(a.out / 'attention.json', records)
    summary = {'status': 'FAIL' if fatal else 'PASS', 'conditions': len(records),
               'conditions_passed_integer_execution': sum(r['status'] == 'PASS' for r in records),
               'conditions_failed_integer_execution': sum(r['status'] != 'PASS' for r in records),
               'full_model_quality_accepted': False, 'hardware_implemented': False,
               'source': source, 'input_captures': inputs, 'LUTs': lut_meta,
               'environment': {'python': platform.python_version(), 'numpy': np.__version__, 'platform': platform.platform()},
               'seconds': time.monotonic() - start, 'scope': __doc__,
               'protocol': {'schema': 'integer-attention-candidate/1', 'sampling': 'first4/last4 prefill and all32 captured decode query positions; complete captured GQA sharing group',
                            'Q': 'dynamic perquery signed8[-127,127], integer exponent after S32Q20 bridge',
                            'KV': 'signed8 or signed16 symmetric[-127,127]/[-32767,32767], perhead dyadic calibrated exponent frozen before evaluation',
                            'score': 'S32Q12 RNE of complete QK times offline U32Q30 head scaling; overflow rejects rather than wraps/saturates',
                            'exp': 'max subtract with actual causal/local mask, RNE LUT index, U32Q30 exp[-16,0], below-16 exactly zero',
                            'probability': 'U64 exp sum; U64(exp<<15)/sum, independent quotient/remainder RNE, saturate to nonnegative P15[0,32767]',
                            'PV': 'S8-valued radix128 matmul passes, I32 partial/shift/add with I64 oracle and declared normalizedP/staticVscale guard',
                            'failure': 'failed range/execution conditions saved and remaining independent conditions continued; five-percent local diagnostic never means full model acceptance'},
               'float_boundaries': ['captured FP32 source -> S32Q20 offline RNE', 'KV static exponent compilation reads original calibration only',
                                    'offline U32Q30 scaling and LUT math.exp compiler', 'FP64 exp/div same-coded-input reference and numerical metrics only'],
               'hardware_limits': ['No full integer norm/RoPE/state/model implementation', 'No isolated target timing, port schedule, RTL, PPA or full-model quality acceptance',
                                   'U64 sum/divisor and signed64 scaling multiply are explicit required candidates, not existing S8 capabilities',
                                   'Psum proof is normalized P15 with immutable Vscale, not online unnormalized O or varying page-scale PV'],
               'artifacts': {f.name: {'bytes': f.stat().st_size, 'sha256': sha(f)} for f in sorted(a.out.iterdir()) if f.is_file()}}
    save(a.out / 'manifest.json', summary)
    print(json.dumps({key: summary[key] for key in ('status', 'conditions', 'conditions_passed_integer_execution', 'conditions_failed_integer_execution', 'seconds')}), flush=True)
    if fatal:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
