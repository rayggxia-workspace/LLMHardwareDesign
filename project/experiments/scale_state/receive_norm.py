"""Independent exact acceptance of Issue66 integer RMSNorm/selected-next candidates.

Never imports norm.py/consumer.py. Python integers, Fraction RNE, math.isqrt
and Decimal offline constants replace the producer arithmetic implementation.
Only source/constant compilation and diagnostic floating references use float.
"""
import argparse
from decimal import Decimal, localcontext, ROUND_HALF_EVEN
from fractions import Fraction
import hashlib
import io
import json
import math
from pathlib import Path
import time
import zipfile
import numpy as np

PROFILES = ('static_ACT8', 'same_range_ACT16', 'tile16_delta_ACT8', 'delta_to_K128_ACT8')


def need(value, label):
    if not value:
        raise AssertionError(label)


def same(a, b, label):
    need(np.array_equal(a, b), label)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n', encoding='utf-8')


def arrays(path):
    with np.load(path, allow_pickle=False) as z:
        return {key: z[key] for key in z.files}


def manifest(folder):
    folder = Path(folder)
    m = load(folder/'manifest.json')
    need(m['status'] in ('PASS', 'FAIL'), 'known producer execution status')
    for name, desc in m['artifacts'].items():
        path = (folder/name).resolve()
        need(path.is_relative_to(folder.resolve()), 'artifact path stays inside source')
        need(path.stat().st_size == desc['bytes'] and sha(path) == desc['sha256'], 'artifact SHA/bytes '+name)
    return m


def pow2(e):
    return Fraction(2)**int(e)


def signed(value, bits=64):
    value = int(value)
    if not -(1 << (bits-1)) <= value < 1 << (bits-1):
        raise OverflowError('signed'+str(bits))
    return value


def unsigned(value, bits):
    value = int(value)
    if not 0 <= value < 1 << bits:
        raise OverflowError('U'+str(bits)+' range')
    return value


def shift_guard(shift):
    if not -63 <= int(shift) <= 63:
        raise OverflowError('RNE shift outside[-63,63]')


def covering_unit(maximum, bound, zero):
    maximum = Fraction(maximum)
    if not maximum:
        return zero
    e = maximum.numerator.bit_length()-maximum.denominator.bit_length()-bound.bit_length()
    while Fraction(bound)*pow2(e) < maximum:
        e += 1
    while Fraction(bound)*pow2(e-1) >= maximum:
        e -= 1
    return e


def constants(raw_gamma, H):
    effective = np.add(np.asarray(raw_gamma, np.float32), np.float32(1))
    gamma = np.array([signed(round(Fraction(float(v))*2**20), 32) for v in effective], np.int32)
    with localcontext() as ctx:
        ctx.prec = 70
        epsilon = int((Decimal('0.000001')*Decimal(2)**40).to_integral_value(rounding=ROUND_HALF_EVEN))
        sqrtH = int((Decimal(H).sqrt()*Decimal(2)**20).to_integral_value(rounding=ROUND_HALF_EVEN))
    unsigned(sqrtH, 32)
    return gamma, epsilon, sqrtH


def rms_oracle(sums, units, gamma, epsilon, sqrtH):
    """All code values independent; no iterative sqrt/division from producer."""
    need(sums.dtype == np.int64 and units.dtype == np.int16 and gamma.dtype == np.int32,
         'norm source typed contract')
    need(sums.shape == units.shape and len(gamma) == sums.shape[1], 'full hidden row shapes')
    R, H = sums.shape
    result = dict(X16=np.zeros((R, H), np.int16), row_exponent=np.zeros(R, np.int16),
                  square_sum_U64=np.zeros(R, np.uint64), Den_U64=np.zeros(R, np.uint64),
                  sqrt_U32=np.zeros(R, np.uint32), inv_Q30_U32=np.zeros(R, np.uint32),
                  before_gamma_S32Q20=np.zeros((R, H), np.int32), norm_S32Q20=np.zeros((R, H), np.int32))
    for r in range(R):
        origin = int(min(units[r]))
        physical, aligned = [], []
        for code, unit in zip(sums[r], units[r]):
            distance = int(unit)-origin
            if distance > 63:
                raise OverflowError('row alignment shift>63')
            aligned.append(signed(int(code) << distance))
            physical.append(Fraction(int(code))*pow2(unit))
        maximum = max(abs(v) for v in physical)
        if not maximum:
            continue  # Explicit zero row: e/Den/root/inverse and outputs stay zero.
        e = covering_unit(maximum, 32767, 0)
        signed(e, 16)
        shift_guard(e-origin)
        x = [round(v/pow2(e)) for v in physical]
        need(all(-32767 <= v <= 32767 for v in x), 'exact coverage symmetric X16')
        Z = unsigned(sum(v*v for v in x), 64)
        epsilon_product = unsigned(int(epsilon)*H, 64)
        epsilon_shift = 24+2*e
        shift_guard(epsilon_shift)
        epsilon_term = round(Fraction(epsilon_product)*pow2(-epsilon_shift))
        den = unsigned((Z << 16)+epsilon_term, 64)
        if not den:
            raise ValueError('nonzero row has zero denominator')
        root = unsigned(math.isqrt(den), 32)
        need(root*root <= den < (root+1)**2, 'isqrt floor certificate')
        numerator = unsigned(int(sqrtH) << 18, 64)
        inverse = round(Fraction(numerator, root))
        if inverse >= 1 << 32:
            raise OverflowError('inverse U32Q30')
        result['X16'][r] = x
        result['row_exponent'][r] = e
        result['square_sum_U64'][r] = Z
        result['Den_U64'][r] = den
        result['sqrt_U32'][r] = root
        result['inv_Q30_U32'][r] = inverse
        for c in range(H):
            product = signed(x[c]*inverse)
            normal = signed(round(Fraction(product, 1 << 10)), 32)
            weighted = signed(normal*int(gamma[c]))
            y = signed(round(Fraction(weighted, 1 << 20)), 32)
            result['before_gamma_S32Q20'][r, c] = normal
            result['norm_S32Q20'][r, c] = y
    return result


def compare_norm(stored, expected):
    for field, value in expected.items():
        need(stored[field].dtype == value.dtype, 'norm dtype '+field)
        same(stored[field], value, 'independent norm code '+field)


def encode_a8(codes):
    R, H = codes.shape
    need(H % 128 == 0 and codes.dtype == np.int32, 'integer next A8 full K128')
    result = np.empty((R, H), np.int8)
    exponents = np.empty((R, H//128), np.int8)
    for r in range(R):
        for group, start in enumerate(range(0, H, 128)):
            block = [int(v) for v in codes[r, start:start+128]]
            # Fresh encoding retains at least the original S32Q20 step.
            e = max(-20, covering_unit(max(abs(v) for v in block)*pow2(-20), 127, -20))
            signed(e, 8)
            shift_guard(e+20)
            exponents[r, group] = e
            for c, v in enumerate(block, start):
                q = round(Fraction(v)*pow2(-20-e))
                need(-127 <= q <= 127, 'A8 symmetric coverage')
                result[r, c] = q
    return result, exponents


def compile_weights(raw):
    N, H = raw.shape
    need(H % 128 == 0, 'frozen next W groups')
    w = np.empty((N, H), np.int8)
    we = np.empty((N, H//128), np.int8)
    for n in range(N):
        for g, start in enumerate(range(0, H, 128)):
            block = [Fraction(float(v)) for v in raw[n, start:start+128]]
            e = covering_unit(max(abs(v) for v in block), 127, -30)
            signed(e, 8)
            we[n, g] = e
            for c, value in enumerate(block, start):
                q = round(value/pow2(e))
                need(-127 <= q <= 127, 'independent offline W8 coverage')
                w[n, c] = q
    return w, we


def next_oracle(a, ae, w, we, stored, base):
    R, H = a.shape
    N, G = len(w), H//128
    parts = np.zeros((G, R, N), np.int32)
    units = ae.T[:, :, None].astype(np.int16)+we.T[:, None].astype(np.int16)
    e0 = units.min(axis=0)
    if np.max(units-e0) > 35:
        raise OverflowError('mixed exponent spread guard35')
    need(H*16129*(1 << int(np.max(units-e0))) < 1 << 63, 'full wide linear format guard')
    acc = np.zeros((R, N), np.int64)
    for r in range(R):
        for n in range(N):
            total = 0
            for g in range(G):
                dot = sum(int(a[r, k])*int(w[n, k]) for k in range(g*128, (g+1)*128))
                signed(dot, 32)
                parts[g, r, n] = dot
                total += dot << int(units[g, r, n]-e0[r, n])
            acc[r, n] = signed(total)
    expected = dict(A8=a, Ae=ae, parts=parts, units=units, e0=e0, acc=acc)
    if stored is not None:
        for field, value in expected.items():
            need(stored['next.'+field].dtype == value.dtype, 'next dtype '+field)
            same(stored['next.'+field], value, 'independent next '+field)
    final_units = np.broadcast_to(base.astype(np.int16)[None], (R, N))
    if stored is not None:
        need(stored['next.final_units'].dtype == np.int16 and stored['next.final_ACT8'].dtype == np.int8,
             'final RQ types')
        same(stored['next.final_units'], final_units, 'fixed final base reused')
    sat = 0
    for ix in np.ndindex(acc.shape):
        shift = int(final_units[ix])-int(e0[ix])
        shift_guard(shift)
        q = round(Fraction(int(acc[ix]))*pow2(-shift))
        sat += not -128 <= q <= 127
        if stored is not None:
            need(int(stored['next.final_ACT8'][ix]) == max(-128, min(127, q)), 'final RQ Fraction code')
    return acc, e0, sat


def real(code, unit):
    return np.ldexp(np.asarray(code, np.float64), np.asarray(unit, np.int64))


def rms_float(values, raw_gamma):
    x = np.asarray(values, np.float32)
    variance = np.mean(np.square(x), axis=-1, keepdims=True, dtype=np.float32)
    inverse = np.float32(1)/np.sqrt(variance+np.float32(1e-6))
    return np.multiply(np.multiply(x, inverse), np.add(np.asarray(raw_gamma, np.float32), np.float32(1)))


def metric(a, b):
    a, b = np.asarray(a, np.float64), np.asarray(b, np.float64)
    return dict(relative_rmse=float(np.linalg.norm(a-b)/max(np.linalg.norm(b), 1e-30)),
                max_abs=float(np.max(np.abs(a-b))))


def verify_cost(row, R, H, active):
    counts = row['counts']
    for field in ('X16_Fraction_codes', 'norm_pre_gamma_Fraction_codes', 'norm_gamma_Fraction_codes', 'fresh_A8_Fraction_codes'):
        need(counts[field] == R*H, 'full code count '+field)
    for field, value in dict(isqrt_math_oracles=active, divider_Fraction_oracles=active,
                             isqrt_restoring_rounds=active*32, divide_restoring_rounds=active*64,
                             zero_rows=R-active).items():
        need(counts[field] == value, 'nonzero sqrt/div work '+field)
    cost = row['candidate_cost']
    for field, value in dict(gamma_S32Q20_bytes=H*4, norm_S32Q20_row_bytes=H*4, X16_row_bytes=H*2,
                             mixed_sum_I64_plus_I16_row_bytes=H*10, inverse_U32Q30_bytes_per_row=4,
                             X16_square_products=active*H, U64_square_sum_add_terms=active*H,
                             S8_only_products_per_S16square_upper=9,
                             S16xU32_products=active*H, S32xS32_gamma_products=active*H,
                             S8_only_products_per_S16xU32_upper=15, S8_only_products_per_S32xS32_upper=25).items():
        need(cost[field] == value, 'candidate cost '+field)
    # This receiver revision requires the revised finite-buffer account. The
    # independently frozen old receiver remains applicable to norm01/02; a
    # partial/missing new ledger cannot silently downgrade to that old account.
    need(cost.get('aligned_I64_row_bytes') == H*8, 'aligned row I64 storage')
    need(cost.get('aligned_I64_row_fits_V16KiB') is (H*8 <= 16384), 'aligned row finite V16KiB capacity')
    alternatives = {
        'two_source_passes': {'sum_and_units_read_bytes_per_row': 2*H*(8+2), 'aligned_spill_RW_bytes': 0},
        'aligned_spill': {'sum_and_units_read_bytes_per_row': H*(8+2), 'aligned_spill_RW_bytes': 2*H*8}}
    need(cost.get('finite_buffer_alternatives') == alternatives, 'independent mutually exclusive source/spill routes')
    route = cost.get('selected_candidate_buffer_route', '')
    need(route.startswith('two_source_passes;') and 'software reference storage' in route and
         'not free V SRAM' in route, 'selected two-read route cannot use free aligned storage')
    need(cost.get('fresh_A8_payload_bytes') == R*H, 'fresh A8 payload width')
    need(H % 128 == 0 and cost.get('fresh_A8_K128_exponent_bytes') == R*(H//128),
         'fresh A8 one I8 scale per K128')
    # 128-bit memory beats and 64-byte transport granules are separate. Each
    # packet has a64-byte header and at most1984 bytes of padded payload, thus
    # never exceeds the2KiB FIFO. The32-byte row coordinates are payload.
    payload = H+(H//128)+32
    packet_bytes = 0
    remaining = payload
    while remaining:
        piece = min(remaining, 1984)
        physical = 64+64*((piece+63)//64)
        need(physical <= 2048, 'packet fits finite 2KiB FIFO')
        packet_bytes += physical
        remaining -= piece
    need(cost.get('norm_to_M_row_packet_bytes') == R*packet_bytes,
         'independent A8 scale/coordinate/header/padding transport')
    wanted = dict(
        sum_and_units_two_reads=2*((H*(8+2)+15)//16),
        X16_write_then_norm_read_if_square_fused_at_encoding=2*((H*2+15)//16),
        X16_write_square_read_norm_read_if_not_fused=3*((H*2+15)//16),
        gamma_read=(H*4+15)//16, norm32_write_read=2*((H*4+15)//16),
        fresh_A8_write_read=2*((H+15)//16), fresh_Ae_write_read=2*((H//128+15)//16))
    need(cost['1RW128bit_row_read_write_lower_bound_beats'] == wanted,
         'independent revised per-row 1RW lower bounds including fresh A8/scales')
    scope = cost['buffer_scope']
    need('alternative accounts, not added together' in scope and 'no finite schedule' in scope,
         'mutually exclusive routes and physical scheduling evidence boundary')


def write_npz(path, data):
    with zipfile.ZipFile(path, 'x', zipfile.ZIP_DEFLATED) as z:
        for name, array in sorted(data.items()):
            buf = io.BytesIO()
            np.save(buf, array, allow_pickle=False)
            info = zipfile.ZipInfo(name+'.npy', (2026, 10, 24, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, buf.getvalue())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ('capture', 'consumer', 'integer', 'repeat', 'out'):
        parser.add_argument('--'+flag, type=Path, required=True)
    parser.add_argument('--binding', type=Path)
    args = parser.parse_args()
    need(not args.out.exists(), 'new receiver output file')
    begin = time.monotonic()
    binding = None
    if args.binding:
        binding = load(args.binding)
        need(binding['receive_norm_sha256'] == sha(__file__) and len(binding['commit']) == 40,
             'independent receiver source/commit binding')
    capture, consumer, m1, m2 = (manifest(p) for p in (args.capture, args.consumer, args.integer, args.repeat))
    need(capture['status'] == consumer['status'] == 'PASS', 'accepted raw/consumer input')
    need(m1['artifacts'] == m2['artifacts'], 'two-round all scientific artifacts SHA/bytes')
    need(m1['source_commit'] == m2['source_commit'] and m1['norm_sha256'] == m2['norm_sha256'] and
         m1['consumer_dependency_sha256'] == m2['consumer_dependency_sha256'], 'two-round producer source')
    for meta in (m1, m2):
        need(meta['capture_manifest_sha256'] == sha(args.capture/'manifest.json') and
             meta['consumer_manifest_sha256'] == sha(args.consumer/'manifest.json'), 'norm exact input binding')
        need(meta['float_runtime_fallback'] is False and meta['whole_integer_model_qualified'] is False,
             'integer candidate/model evidence boundary')
    need(consumer['input_manifest_sha256'] == sha(args.capture/'manifest.json'), 'consumer raw binding')
    chain = capture['chain']
    need(chain['from_layer'] == 3 and chain['to_layer'] == 4 and chain['hidden_size'] == 2560 and
         chain['next_projection_outputs'] == 16 and chain['next_projection_native_outputs'] == 8192 and
         chain['norm_weight_contract'] == 'effective gamma=1+stored weight', 'actual norm/projection topology')
    with np.load(args.capture/'consumer-raw.npz', allow_pickle=False) as raw:
        raw_gamma = raw['weight.next_norm']
        raw_w = raw['weight.next_projection']
        native = {c: raw[c+'.projection'] for c in ('prefill', 'decode')}
    common = arrays(args.consumer/'common.npz')
    H = len(raw_gamma)
    need(H == 2560 and raw_w.shape == (16, H), 'frozen actual fullhidden/selected-next16 scope')
    need(native['prefill'].shape == (8, 16) and native['decode'].shape == (32, 16), 'actual selected capture rows')
    gamma, eps, sqrtH = constants(raw_gamma, H)
    const = arrays(args.integer/'constants.npz')
    same(const['gamma_S32Q20'], gamma, 'all gamma Fraction codes')
    need(const['gamma_S32Q20'].dtype == np.int32 and const['eps_U64Q40'].dtype == np.uint64 and
         const['sqrtH_U32Q20'].dtype == np.uint32, 'compiled constant dtypes')
    need(int(const['eps_U64Q40']) == eps and int(const['sqrtH_U32Q20']) == sqrtH,
         'Decimal offline epsilon/sqrtH compilation')
    w, we = compile_weights(raw_w)
    same(common['next.W8'], w, 'independently compiled next W8')
    same(common['next.We'], we, 'independently compiled next W scale')
    rows = load(args.integer/'norm.json')
    expected_ids = {c+'.'+p for c in ('prefill', 'decode') for p in PROFILES}
    need(len(rows) == 8 and {r['id'] for r in rows} == expected_ids, 'frozen8 norm profiles')
    checks, negative, metrics = [], None, {}
    for row in rows:
        ident = row['id']
        case = ident.split('.')[0]
        old = arrays(args.consumer/(ident+'.npz'))
        actual_rows = 8 if case == 'prefill' else 32
        need(old['sum_acc64'].shape == (actual_rows, H) and old['sum_units'].shape == (actual_rows, H),
             'all captured consumer rows/full hidden preserved')
        try:
            expected = rms_oracle(old['sum_acc64'], old['sum_units'], gamma, eps, sqrtH)
        except (OverflowError, ValueError) as error:
            need(row['status'] == 'FAIL' and row['parameters_retuned'] is False, 'guard failure not preserved')
            checks.append(dict(id=ident, status='GUARD_FAILURE_INDEPENDENTLY_CONFIRMED', error=str(error)))
            continue
        if row['status'] == 'FAIL':
            try:
                trial_a, trial_e = encode_a8(expected['norm_S32Q20'])
                next_oracle(trial_a, trial_e, w, we, None, common['next.Ybase'])
            except (OverflowError, ValueError) as error:
                need(row['parameters_retuned'] is False, 'next guard failure was retuned')
                checks.append(dict(id=ident, status='GUARD_FAILURE_INDEPENDENTLY_CONFIRMED', error=str(error)))
                continue
            raise AssertionError('producer failed but complete norm/next oracle succeeded')
        need(row['status'] == 'PASS', 'integer norm oracle succeeded but producer failed')
        stored = arrays(args.integer/(ident+'.npz'))
        compare_norm(stored, expected)
        a, ae = encode_a8(expected['norm_S32Q20'])
        acc, e0, sat = next_oracle(a, ae, w, we, stored, common['next.Ybase'])
        need(row['final_RQ']['saturation'] == sat and row['final_RQ']['Fraction_output_codes'] == acc.size,
             'final RQ saturation/count diagnostics')
        R = len(a)
        need(row['rows'] == R and row['hidden'] == H, 'reported complete norm scope')
        ni = row['next_integer']
        need(ni['group'] == 128 and ni['groups'] == H//128 and ni['MACs'] == R*H*len(w) and
             ni['INT64_partial_values_checked'] == (H//128)*R*len(w), 'complete next matrix work counts')
        active = int(np.count_nonzero(expected['square_sum_U64']))
        verify_cost(row, R, H, active)
        reencoded = real(expected['X16'], expected['row_exponent'][:, None])
        ref_x16 = rms_float(reencoded.astype(np.float32), raw_gamma)
        norm_real = real(expected['norm_S32Q20'], -20)
        physical_next = real(acc, e0)
        observed = dict(X16_reencoding_vs_input_sum=metric(reencoded, real(old['sum_acc64'], old['sum_units'])),
                        FPnorm_after_X16_vs_original_FPnorm=metric(ref_x16, old['norm_F32_bridge']),
                        integer_norm_vs_FPnorm_on_X16=metric(norm_real, ref_x16),
                        integer_norm_vs_original_FPnorm=metric(norm_real, old['norm_F32_bridge']),
                        next_projection_vs_original_FPnorm_chain=metric(physical_next, real(old['next.acc'], old['next.e0'])),
                        next_projection_vs_native=metric(physical_next, native[case]))
        for field, values in observed.items():
            for stat, value in values.items():
                need(math.isclose(row[field][stat], value, rel_tol=1e-7, abs_tol=1e-9), 'independent metric '+field)
        need(row['fresh_A8_source'] == 'integer S32Q20, no floating bridge or encode_rows' and
             row['integer_norm_candidate'] and not row['full_integer_model_qualified'] and
             not row['hardware_performance_accepted'], 'candidate evidence boundary')
        metrics[ident] = observed
        checks.append(dict(id=ident, status='PASS_INDEPENDENT_INTEGER', rows=R, hidden=H,
                           full_norm_Fraction_codes=R*H, next_Pythonint_products=R*H*len(w),
                           isqrt_floor_certificates=active, inverse_Fraction_RNE=active,
                           zero_shortcut_rows=R-active, final_RQ_saturations=sat))
        if negative is None:
            corrupt = dict(stored)
            corrupt['norm_S32Q20'] = stored['norm_S32Q20'].copy()
            corrupt['norm_S32Q20'][0, 0] += 1
            path = args.out.with_name(args.out.stem+'-rehashed-norm-code.npz')
            write_npz(path, corrupt)
            specimen = dict(bytes=path.stat().st_size, sha256=sha(path))
            save(path.with_suffix('.json'), specimen)
            need(sha(path) == specimen['sha256'], 'negative refreshed SHA accepted')
            try:
                compare_norm(arrays(path), expected)
            except AssertionError as error:
                need('independent norm code norm_S32Q20' in str(error), 'negative semantic rejection reason')
                negative = dict(artifact=path.name, specimen=specimen, rewritten_SHA_passed=True,
                                independent_semantic_rejected=True, error=str(error))
            else:
                raise AssertionError('rehashed actual norm code accepted')
    accepted = sum(r['status'] == 'PASS_INDEPENDENT_INTEGER' for r in checks)
    need(m1['passed'] == accepted and m1['conditions'] == 8, 'producer pass/fail tally')
    receipt = dict(status='PASS_INDEPENDENT_ACCEPTANCE', receiver_sha256=sha(__file__), source_binding=binding,
                   capture_manifest_sha256=sha(args.capture/'manifest.json'),
                   consumer_manifest_sha256=sha(args.consumer/'manifest.json'),
                   integer_manifest_sha256=sha(args.integer/'manifest.json'),
                   repeat_manifest_sha256=sha(args.repeat/'manifest.json'),
                   all_scientific_artifacts_two_round_SHA_bytes_identical=True,
                   conditions=checks, passed=accepted, guard_failures=8-accepted, metrics=metrics,
                   all_gamma_Fraction_codes=H, all_next_weight_Fraction_codes=raw_w.size,
                   negative=negative, seconds=time.monotonic()-begin,
                   source_and_diagnostics_float_only=True, full_integer_model_qualified=False,
                   target_timing_or_PPA_accepted=False,
                   scope='Full2560hidden RMS candidate and next16 outputs only; upstream capture/compiler remain explicit boundaries. All8 profiles independently replayed once, complete second-round scientific artifacts SHA/bytes checked. Guard failures remain failures. 1RW and S8 product costs are candidate lower/upper bounds, not scheduled target hardware.')
    save(args.out, receipt)
    print(dict(status=receipt['status'], passed=accepted, guard_failures=8-accepted))


if __name__ == '__main__':
    main()
