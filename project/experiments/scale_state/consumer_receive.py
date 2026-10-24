"""Independent consumer artifact receiver; never imports producer arithmetic.

Replays one complete integer chain after proving the two rounds byte-identical.
FP32 full-hidden norm is an explicit bridge, selected next16 is not full GDN,
and packet/1RW counts are lower bounds rather than hardware timing or PPA.
"""
import argparse
from fractions import Fraction
import hashlib
import io
import json
from pathlib import Path
import zipfile
import numpy as np

PROFILES = ('static_ACT8', 'same_range_ACT16', 'tile16_delta_ACT8', 'delta_to_K128_ACT8')


def need(ok, text):
    if not ok:
        raise ValueError(text)


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 << 20), b''): h.update(block)
    return h.hexdigest()


def load(path):
    return json.loads(Path(path).read_text())


def arrays(path):
    with np.load(path, allow_pickle=False) as z:
        return {key: z[key] for key in z.files}


def artifact(directory, manifest):
    for name, desc in manifest['artifacts'].items():
        path = (directory/name).resolve()
        need(path.is_relative_to(directory.resolve()), 'artifact path')
        need(path.stat().st_size == desc['bytes'] and sha(path) == desc['sha256'], 'artifact SHA/size '+name)


def binary_power(exponent):
    exponent = int(exponent)
    return Fraction(1 << exponent) if exponent >= 0 else Fraction(1, 1 << -exponent)


def nearest(value):
    # Fraction's exact numerator/denominator round-to-nearest-even is the oracle.
    return round(value)


def real(code, unit):
    return np.asarray(code, dtype=np.float64)*np.exp2(np.asarray(unit, dtype=np.float64))


def metric(value, reference):
    r = np.asarray(reference, dtype=np.float64); difference = np.asarray(value, dtype=np.float64)-r
    return {'relative_rmse': float(np.linalg.norm(difference)/max(np.linalg.norm(r), 1e-30)),
            'max_abs': float(np.max(abs(difference)))}


def float_bridge(value):
    rounded = np.rint(np.asarray(value, dtype=np.float64)*1048576)
    need(np.isfinite(rounded).all() and rounded.min() >= -(1 << 31) and rounded.max() < 1 << 31, 'S32Q20 range')
    return rounded.astype(np.int32)


def compile_dyadic(values, group=None, twice=False):
    x = np.asarray(values, dtype=np.float64)
    maximum = np.max(abs(x.reshape(x.shape[0], x.shape[1]//group, group)), axis=-1) if group else np.max(abs(x), axis=0)
    if twice: maximum *= 2
    # frexp independently determines ceil(log2(max/127)); no producer log2.
    result = np.full(maximum.shape, -30, dtype=np.int16)
    valid = maximum > 0
    mantissa, exponent = np.frexp(maximum[valid]/127)
    result[valid] = exponent-(mantissa == .5)
    need(result.min() >= -128 and result.max() <= 127, 'compiled exponent range')
    if group:
        codes = np.rint(np.ldexp(x.reshape(x.shape[0], x.shape[1]//group, group), -result[:, :, None])).clip(-127, 127).astype(np.int8).reshape(x.shape)
        return codes, result.astype(np.int8)
    return result.astype(np.int8)


def encode(value):
    source = float_bridge(value); rows, K = source.shape
    need(K % 128 == 0, 'K128 tail')
    codes = np.empty(source.shape, dtype=np.int8); exponents = np.empty((rows, K//128), dtype=np.int8)
    witnesses = 0
    for row in range(rows):
        for g, start in enumerate(range(0, K, 128)):
            block = source[row, start:start+128]; maximum = int(np.max(abs(block.astype(np.int64))))
            shift = max(0, maximum.bit_length()-7)
            if maximum > 127*(1 << shift): shift += 1
            e = shift-20; exponents[row, g] = e
            # S32 has at most31 magnitude bits; this power-of-two FP64
            # division is exact before independently supplied IEEE RNE.
            q = np.rint(np.ldexp(block.astype(np.float64), -shift)).astype(np.int64)
            need(np.max(abs(q)) <= 127, 'A coverage')
            codes[row, start:start+128] = q
            for j in [0, 127]:
                need(int(q[j]) == nearest(Fraction(int(block[j]), 1 << shift)), 'Fraction A endpoint')
                witnesses += 1
    return source, codes, exponents, witnesses


def rms(value, raw_gamma):
    x = np.asarray(value, dtype=np.float32)
    squares = np.square(x)
    mean = np.sum(squares, axis=1, dtype=np.float32)/np.float32(x.shape[1])
    inverse = np.float32(1)/np.sqrt(mean+np.float32(1e-6))
    result = np.multiply(x, inverse[:, None])
    return np.multiply(result, np.add(np.asarray(raw_gamma, dtype=np.float32), np.float32(1)))


def linear_check(a, ae, w, we, stored, full_python=False):
    R, K = a.shape; N = len(w); G = K//128
    need(stored['parts'].shape == (G, R, N) and stored['parts'].dtype == np.int32, 'linear partial shape/type')
    need(stored['units'].dtype == np.int16 and stored['e0'].dtype == np.int16 and stored['acc'].dtype == np.int64, 'linear unit/accumulator dtype')
    unit = ae.T[:, :, None].astype(np.int16)+we.T[:, None, :].astype(np.int16)
    e0 = np.min(unit, axis=0); delta = unit-e0[None]
    need(np.array_equal(stored['units'], unit) and np.array_equal(stored['e0'], e0), 'product/common scale units')
    need(delta.max() <= 35 and K*16129*(1 << int(delta.max())) < 1 << 63, 'wide format certificate')
    accumulator = np.zeros((R, N), dtype=np.int64)
    for g in range(G):
        sl = slice(g*128, (g+1)*128)
        oracle = a[:, sl].astype(np.int64) @ w[:, sl].astype(np.int64).T
        need(np.array_equal(oracle, stored['parts'][g]), 'all I64 group dots')
        accumulator += np.left_shift(oracle, delta[g])
    need(np.array_equal(accumulator, stored['acc']), 'complete wide reduction')
    columns = range(N) if full_python else sorted({0, min(15, N-1), min(16, N-1), N//2, N-1})
    checks = 0
    for row in range(R):
        for col in columns:
            total = sum(int(stored['parts'][g, row, col])*(1 << int(delta[g, row, col])) for g in range(G))
            need(total == int(accumulator[row, col]), 'arbitrary integer sum')
            exact_physical = sum((Fraction(int(stored['parts'][g, row, col]))*binary_power(unit[g, row, col]) for g in range(G)), Fraction(0))
            need(exact_physical == Fraction(int(accumulator[row, col]))*binary_power(e0[row, col]), 'Fraction mixed-unit reduction')
            checks += 1
    return accumulator, e0, {'I64_partial_values': int(stored['parts'].size), 'arbitrary_integer_reductions': checks,
                            'Fraction_mixed_unit_terms': checks*G}


def fields(common, prefix):
    return {name: common[prefix+name] for name in ['parts', 'units', 'e0', 'acc']}


def quant_check(acc, units, exponents, code, bits):
    low, high = (-128, 127) if bits == 8 else (-32768, 32512)
    need(code.dtype == np.dtype('int8' if bits == 8 else 'int16'), 'outlet code dtype')
    saturations = 0
    for index in np.ndindex(acc.shape):
        value = nearest(Fraction(int(acc[index]))*binary_power(int(units[index])-int(exponents[index])))
        saturations += value < low or value > high
        need(int(code[index]) == max(low, min(high, value)), 'Fraction outlet/final code')
    return int(code.size), int(saturations)


def delta_check(acc, units, base, delta):
    R, H = acc.shape; need(delta.shape == (R, H//16) and delta.dtype == np.int8, 'tile delta dtype/shape')
    checks = 0
    for row in range(R):
        for tile, start in enumerate(range(0, H, 16)):
            d = int(delta[row, tile]); need(-16 <= d <= 16, 'delta domain')
            if not np.any(acc[row, start:start+16]):
                need(d == 0, 'zero tile delta'); continue
            def fits(candidate):
                nonlocal checks
                values = [nearest(Fraction(int(acc[row, j]))*binary_power(int(units[row, j])-int(base[j])-candidate)) for j in range(start, start+16)]
                checks += 16
                return all(-128 <= v <= 127 for v in values)
            need(fits(d), 'delta does not cover full tile')
            # RNE admissibility is monotonic as the dyadic step grows. Failing
            # the immediately finer candidate proves the recorded d minimal.
            need(d == -16 or not fits(d-1), 'delta was not finest admissible')
    return checks


def k128_check(code, unit, actual, actual_unit, group_unit):
    R, H = code.shape; need(group_unit.shape == (R, H//128), 'K128 metadata shape')
    for row in range(R):
        for group, start in enumerate(range(0, H, 128)):
            origin = int(unit[row, start:start+128].min())
            magnitude = max(abs(int(code[row, j]) << (int(unit[row, j])-origin)) for j in range(start, start+128))
            shift = max(0, magnitude.bit_length()-7)
            if magnitude > 127*(1 << shift): shift += 1
            expected = origin+shift
            need(int(group_unit[row, group]) == expected, 'K128 integer max/scale')
            for col in range(start, start+128):
                need(int(actual_unit[row, col]) == expected, 'K128 published common unit')
                q = nearest(Fraction(int(code[row, col]))*binary_power(int(unit[row, col])-expected))
                need(-127 <= q <= 127 and q == int(actual[row, col]), 'Fraction K128 conversion')
    return int(code.size)


def packet(payload):
    total = 0
    while payload:
        size = min(payload, 1984); total += 64+64*((size+63)//64); payload -= size
    return total


def check_cost(record, R, H, K, N, profile, code):
    c = record['costs']; width = code.dtype.itemsize; dynamic = 'delta' in profile
    extra = H//128 if profile == 'delta_to_K128_ACT8' else H//16 if dynamic else 0
    expected = {'rows': R, 'complete_hidden_channels': H, 'next_projection_selected_outputs': N,
                'source_down_full_K': K, 'ACT_payload_bytes': int(code.nbytes), 'static_base_exponent_bytes': H,
                'incoming_tile16_delta_bytes': R*(H//16) if dynamic else 0,
                'outgoing_scale_metadata_bytes': R*extra,
                'complete_row_packet_bytes_static_base_resident': R*packet(H*width+32+extra),
                'initial_base_scale_wire_bytes': packet(H),
                'original_outlet_per16output_tile_packet_bytes_explicit_scale': R*(H//16)*packet(16*width+16+32+(1 if dynamic else 0)),
                'one_row_exact_residual_S64_plus_I16_units_bytes': H*10,
                'one_row_F32_norm_buffer_bytes': H*4, 'F32_norm_gamma_bytes': H*4,
                'down_W8_total_bytes': H*K, 'down_W128_exponent_total_bytes': H*(K//128),
                'one16output_down_W128_scale_bytes': 16*(K//128),
                'one16output_fixed_W_L1_U32_certificate_bytes_if_used': 16*(K//128)*4,
                'next_projection_W8_bytes': N*H, 'next_projection_W128_scale_bytes': N*(H//128)}
    for name, value in expected.items(): need(c[name] == value, 'cost '+name)
    need(c['norm_V16KiB_capacity'] == {'exact_sum_and_units_fit': H*10 <= 16384, 'one_inplace_F32_row_fits': H*4 <= 16384,
                                      'row_and_gamma_simultaneously_fit': H*8 <= 16384}, 'norm capacity')
    beats = c['single128bit_1RW_bank_lower_bound_beats']
    need(beats == {'ACT_write_read': 2*((H*width+15)//16)*R, 'wide_sum_write_read': 2*((H*8+15)//16)*R,
                   'unit_write_read': 2*((H*2+15)//16)*R, 'norm_gamma_read': ((H*4+15)//16)*R}, '1RW beats')
    need('fresh A8K128' in c['next_projection_input'] and 'no finite scheduler' in c['scope'], 'cost evidence boundary')


def verify_profile(z, case, profile, common, raw, record, nw, ne, base, next_base):
    prefix = case+'.down.'; down = fields(common, prefix); acc, e0 = down['acc'], down['e0']
    R, H = acc.shape; N = len(nw); K = raw['weight.down'].shape[1]
    dynamic = 'delta' in profile; bits = 16 if profile == 'same_range_ACT16' else 8
    exponent = np.broadcast_to(base.astype(np.int16)[None], acc.shape).copy()
    counts = {}
    for name, dtype in [('outlet_units', np.int16), ('residual_S32Q20', np.int32), ('sum_acc64', np.int64),
                        ('sum_units', np.int16), ('sum_F32_bridge', np.float32), ('norm_F32_bridge', np.float32),
                        ('norm_source_S32Q20', np.int32), ('next.A8', np.int8), ('next.Ae', np.int8),
                        ('next.final_ACT8', np.int8), ('next.final_units', np.int16), ('K128_exponents', np.int8)]:
        need(z[name].dtype == dtype, 'declared dtype '+name)
    need(z['outlet_delta'].dtype == np.int8, 'delta metadata dtype')
    if bits == 16: exponent -= 8
    if dynamic:
        counts['Fraction_delta_admissibility_terms'] = delta_check(acc, e0, base, z['outlet_delta'])
        exponent += np.repeat(z['outlet_delta'].astype(np.int16), 16, axis=1)
    else: need(z['outlet_delta'].shape == (R, 0), 'unexpected dynamic metadata')
    need(np.array_equal(exponent, z['outlet_units']), 'outlet per-channel base+delta')
    counts['Fraction_outlet_codes'], sat = quant_check(acc, e0, exponent, z['outlet_codes'], bits)
    if profile == 'delta_to_K128_ACT8':
        need(z['transport_codes'].dtype == np.int8 and z['transport_units'].dtype == np.int8, 'K128 transport format')
        counts['Fraction_K128_conversion'] = k128_check(z['outlet_codes'], exponent, z['transport_codes'], z['transport_units'], z['K128_exponents'])
    else:
        need(z['transport_codes'].dtype == z['outlet_codes'].dtype and z['transport_units'].dtype == np.int16, 'transport format')
        need(np.array_equal(z['transport_codes'], z['outlet_codes']) and np.array_equal(z['transport_units'], exponent), 'unrequested transport conversion')
        need(z['K128_exponents'].shape == (R, 0), 'unrequested K128 metadata')
    residual = float_bridge(raw[case+'.residual'])
    need(np.array_equal(residual, z['residual_S32Q20']), 'residual bridge all codes')
    unit = np.minimum(z['transport_units'], -20)
    need(np.array_equal(unit, z['sum_units']), 'residual common units')
    for index in np.ndindex(acc.shape):
        left = Fraction(int(z['transport_codes'][index]))*binary_power(z['transport_units'][index])
        right = Fraction(int(residual[index]), 1 << 20)
        need(Fraction(int(z['sum_acc64'][index]))*binary_power(unit[index]) == left+right, 'Fraction exact residual sum')
        origin = int(unit[index])
        for operand in [int(z['transport_codes'][index]) << (int(z['transport_units'][index])-origin),
                        int(residual[index]) << (-20-origin), int(z['sum_acc64'][index])]:
            need(-(1 << 63) <= operand < 1 << 63, 'I64 residual operand/add range')
    counts['Fraction_residual_values'] = int(acc.size)
    sum_f32 = real(z['sum_acc64'], unit).astype(np.float32)
    need(np.array_equal(sum_f32, z['sum_F32_bridge']), 'sum FP32 bridge')
    norm = rms(sum_f32, raw['weight.next_norm'])
    need(np.array_equal(norm, z['norm_F32_bridge']), 'complete-hidden FP32 RMSNorm recipe')
    source, a8, ae, witness = encode(norm)
    need(np.array_equal(source, z['norm_source_S32Q20']) and np.array_equal(a8, z['next.A8']) and np.array_equal(ae, z['next.Ae']), 'all norm source/A8/unit codes')
    counts['norm_A_codes'] = int(a8.size); counts['Fraction_norm_A_endpoints'] = witness
    nxt = fields(z, 'next.')
    na, nu, stat = linear_check(a8, ae, nw, ne, nxt, full_python=True)
    counts.update({'next_'+key: value for key, value in stat.items()})
    final_unit = np.broadcast_to(next_base.astype(np.int16)[None], na.shape)
    need(np.array_equal(z['next.final_units'], final_unit), 'final projection static unit')
    counts['Fraction_next_final_codes'], final_sat = quant_check(na, nu, final_unit, z['next.final_ACT8'], 8)
    upstream = real(acc, e0); outlet = real(z['outlet_codes'], exponent); transport = real(z['transport_codes'], z['transport_units'])
    next_real = real(na, nu)
    native_next = real(common[case+'.native_norm_projection.acc'], common[case+'.native_norm_projection.e0'])
    no_rq_next = real(common[case+'.pre_outlet.next.acc'], common[case+'.pre_outlet.next.e0'])
    checks = {'upstream_down_before_outlet_RQ_vs_native': metric(upstream, raw[case+'.down']),
              'down_after_outlet_RQ_vs_native': metric(outlet, raw[case+'.down']),
              'transport_requant_vs_outlet': metric(transport, outlet),
              'sum_vs_native': metric(sum_f32, raw[case+'.sum']), 'norm_vs_native': metric(norm, raw[case+'.norm']),
              'next_projection_vs_native': metric(next_real, raw[case+'.projection']),
              'next_projection_vs_native_norm_same_W8A8': metric(next_real, native_next),
              'next_projection_vs_upstream_no_outlet_RQ': metric(next_real, no_rq_next),
              'native_norm_W8A8_vs_native_projection': metric(native_next, raw[case+'.projection']),
              'next_final_ACT8_vs_native': metric(real(z['next.final_ACT8'], final_unit), raw[case+'.projection'])}
    for name, values in checks.items():
        for field, value in values.items(): need(abs(record[name][field]-value) <= 1e-11*max(1., abs(value)), 'metric '+name+'.'+field)
    need(record['costs']['integer_work']['saturation'] == sat and record['next_final_RQ']['saturation'] == final_sat, 'saturation count')
    need(record['integer_norm_implemented'] is False and record['complete_next8192_projection'] is False
         and record['full_model_quality_accepted'] is False and record['hardware_performance_accepted'] is False, 'evidence boundaries')
    check_cost(record, R, H, K, N, profile, z['transport_codes'])
    return counts


def write_npz(path, data):
    with zipfile.ZipFile(path, 'x', zipfile.ZIP_DEFLATED) as z:
        for name, value in sorted(data.items()):
            stream = io.BytesIO(); np.save(stream, value, allow_pickle=False)
            info = zipfile.ZipInfo(name+'.npy', (2026, 10, 24, 0, 0, 0)); info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, stream.getvalue())


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--capture', type=Path, required=True); p.add_argument('--input', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True); p.add_argument('--negative-dir', type=Path)
    a = p.parse_args(); need(not a.out.exists(), 'refuse output overwrite')
    capture = load(a.capture/'manifest.json'); artifact(a.capture, capture)
    need(capture['model']['id'] == 'Qwen/Qwen3.5-4B' and not capture.get('sealed_reserved'), 'model scope')
    raw = arrays(a.capture/'consumer-raw.npz')
    root = [a.input/'consumer01', a.input/'consumer02']; manifests = [load(r/'manifest.json') for r in root]
    for r, m in zip(root, manifests):
        need(m['status'] == 'PASS' and m['conditions'] == 8, 'producer status/conditions')
        need(m['input_manifest_sha256'] == sha(a.capture/'manifest.json') and m['input_artifact_sha256'] == sha(a.capture/'consumer-raw.npz'), 'capture binding')
        artifact(r, m)
    need(manifests[0]['source'] == manifests[1]['source'], 'two rounds source binding')
    need(set(manifests[0]['artifacts']) == set(manifests[1]['artifacts']), 'two rounds file set')
    for name in manifests[0]['artifacts']: need((root[0]/name).read_bytes() == (root[1]/name).read_bytes(), 'round byte mismatch '+name)
    common = arrays(root[0]/'common.npz'); records = load(root[0]/'consumer.json')
    need(len(records) == 8 and {(r['case'], r['profile']) for r in records} == {(c, p) for c in ('prefill', 'decode') for p in PROFILES}, 'eight frozen conditions')
    qw, we = compile_dyadic(raw['weight.down'], 128); nw, ne = compile_dyadic(raw['weight.next_projection'], 128)
    base = compile_dyadic(raw['calibration.down'], twice=True); next_base = compile_dyadic(raw['calibration.projection'], twice=True)
    for name, value in [('down.W8', qw), ('down.We', we), ('next.W8', nw), ('next.We', ne), ('down.Ybase', base), ('next.Ybase', next_base), ('next.raw_norm_weight', raw['weight.next_norm'])]:
        need(common[name].dtype == value.dtype and np.array_equal(common[name], value), 'independent fixed weight/base '+name)
    totals = {}; references = {}
    for case in ('calibration', 'prefill', 'decode'):
        reference_checks = {'down': metric(raw[case+'.A']@raw['weight.down'].T, raw[case+'.down']),
                            'sum': metric(raw[case+'.down']+raw[case+'.residual'], raw[case+'.sum']),
                            'norm': metric(rms(raw[case+'.sum'], raw['weight.next_norm']), raw[case+'.norm']),
                            'projection': metric(raw[case+'.norm']@raw['weight.next_projection'].T, raw[case+'.projection'])}
        need(all(v['relative_rmse'] <= 1e-5 and v['max_abs'] <= 2e-3 for v in reference_checks.values()), 'independent native complete-hidden chain')
        references[case] = reference_checks
    for case in ('prefill', 'decode'):
        for name in ['down', 'residual', 'sum', 'norm', 'projection', 'rows']:
            need(common[case+'.reference.'+name].dtype == raw[case+'.'+name].dtype and
                 np.array_equal(common[case+'.reference.'+name], raw[case+'.'+name]), 'native source '+case+'.'+name)
        s32, aa, ae, aw = encode(raw[case+'.A'])
        need(np.array_equal(common[case+'.down.source_S32Q20'], s32) and np.array_equal(common[case+'.down.A8'], aa)
             and np.array_equal(common[case+'.down.Ae'], ae), 'full down input encoding')
        need(common[case+'.down.source_S32Q20'].dtype == np.int32 and common[case+'.down.A8'].dtype == np.int8
             and common[case+'.down.Ae'].dtype == np.int8, 'down source/A8/scale dtypes')
        acc, unit, stat = linear_check(aa, ae, qw, we, fields(common, case+'.down.'))
        totals[case+'.down'] = {**stat, 'all_A8_codes': int(aa.size), 'Fraction_A_endpoints': aw}
        for prefix, norm in [(case+'.native_norm_projection.', raw[case+'.norm']),
                             (case+'.pre_outlet.next.', rms((real(acc, unit)+real(float_bridge(raw[case+'.residual']), -20)).astype(np.float32), raw['weight.next_norm']))]:
            _, oracle_a, oracle_ae, _ = encode(norm)
            linear_check(oracle_a, oracle_ae, nw, ne, fields(common, prefix), full_python=True)
    for record in records:
        case, profile = record['case'], record['profile']
        data = arrays(root[0]/(case+'.'+profile+'.npz'))
        totals[case+'.'+profile] = verify_profile(data, case, profile, common, raw, record, nw, ne, base, next_base)
    # Persist an actually mutated NPZ and rewritten checksum manifest, validate
    # that checksum, then require the independent numeric receiver to reject it.
    negative = a.negative_dir or a.out.with_name(a.out.stem+'-negative')
    need(not negative.exists(), 'refuse negative specimen overwrite'); negative.mkdir(parents=True)
    specimen = arrays(root[0]/'prefill.static_ACT8.npz'); old = int(specimen['outlet_codes'][0, 0])
    specimen['outlet_codes'][0, 0] = old+1 if old < 127 else old-1
    file = negative/'prefill.static_ACT8.npz'; write_npz(file, specimen)
    altered = {'schema': 'actual-consumer-negative-specimen/1', 'original_source_manifest_sha256': sha(root[0]/'manifest.json'),
               'artifacts': {file.name: {'bytes': file.stat().st_size, 'sha256': sha(file)}}}
    (negative/'manifest.json').write_text(json.dumps(altered, indent=2)+'\n')
    artifact(negative, altered)
    try:
        verify_profile(arrays(file), 'prefill', 'static_ACT8', common, raw,
                       next(r for r in records if r['case'] == 'prefill' and r['profile'] == 'static_ACT8'), nw, ne, base, next_base)
    except ValueError as exc:
        rejection = str(exc); need('Fraction outlet' in rejection, 'negative rejected for unrelated reason')
    else: raise ValueError('rehash actual code mutation escaped')
    receipt = {'status': 'PASS', 'independent': True, 'receiver_sha256': sha(__file__),
               'source': manifests[0]['source'], 'capture_manifest_sha256': sha(a.capture/'manifest.json'),
               'scientific_files_byte_identical': len(manifests[0]['artifacts']), 'conditions_replayed': 8,
               'second_round_scope': 'every indexed file byte-identical; integer arithmetic replayed once',
               'counts': totals, 'native_bridge_checks': references,
               'negative': {'specimen': str(file), 'manifest': str(negative/'manifest.json'), 'sha256': sha(file), 'rehash_check': 'PASS', 'numeric_rejection': rejection,
                            'scope': 'actual profile NPZ+standalone rewritten specimen manifest, unchanged common/captured inputs; no full-batch recapture claim'},
               'scope': __doc__, 'hardware_performance_accepted': False, 'full_integer_norm_qualified': False}
    a.out.parent.mkdir(parents=True, exist_ok=True); a.out.write_text(json.dumps(receipt, indent=2)+'\n', newline='\n')
    print(json.dumps({'status': 'PASS', 'conditions_replayed': 8, 'receipt': str(a.out)}))


if __name__ == '__main__': main()
