"""Qwen3.5 full-hidden down/residual/norm/selected-next-projection reference.

FP32 captured source -> S32Q20, offline weight/Y compilers and full-hidden
FP32 RMSNorm are explicit float boundaries. Other arithmetic is integer with
independent witnesses. This is neither a full integer model nor target timing.
"""
import argparse
from fractions import Fraction
import hashlib
import io
import json
from pathlib import Path
import platform
import subprocess
import time
import zipfile
import numpy as np

PROFILES = ('static_ACT8', 'same_range_ACT16', 'tile16_delta_ACT8', 'delta_to_K128_ACT8')


def sha(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(8 << 20), b''):
            h.update(block)
    return h.hexdigest()


def save(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False)+'\n', newline='\n')


def npz(path, arrays):
    with zipfile.ZipFile(path, 'x', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for key, value in sorted(arrays.items()):
            data = io.BytesIO(); np.save(data, np.asarray(value), allow_pickle=False)
            entry = zipfile.ZipInfo(key+'.npy', (2026, 10, 24, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(entry, data.getvalue())


def checked(value, bits=64):
    value = int(value)
    if not -(1 << (bits-1)) <= value < (1 << (bits-1)):
        raise OverflowError('signed'+str(bits))
    return value


def rne(value, shift):
    value, shift = int(value), int(shift)
    if not -63 <= shift <= 63:
        raise OverflowError('RNE shift outside[-63,63]')
    if shift <= 0:
        return value << -shift
    q, rem = divmod(abs(value), 1 << shift)
    q += rem > (1 << (shift-1)) or (rem == (1 << (shift-1)) and q % 2)
    return -q if value < 0 else q


def fraction_rne(value):
    sign = -1 if value < 0 else 1
    value = abs(value); q, rem = divmod(value.numerator, value.denominator)
    if 2*rem > value.denominator or (2*rem == value.denominator and q % 2):
        q += 1
    return sign*q


def physical(codes, units):
    return np.asarray(codes, dtype=np.float64)*np.exp2(np.asarray(units, dtype=np.float64))


def error(value, reference):
    reference = np.asarray(reference, dtype=np.float64)
    difference = np.asarray(value, dtype=np.float64)-reference
    return {'relative_rmse': float(np.linalg.norm(difference)/max(np.linalg.norm(reference), 1e-30)),
            'max_abs': float(np.max(abs(difference)))}


def bridge(value):
    raw = np.rint(np.asarray(value, dtype=np.float64)*2.**20)
    if not np.isfinite(raw).all() or raw.min() < -(1 << 31) or raw.max() >= 1 << 31:
        raise OverflowError('FP32->S32Q20 bridge')
    return raw.astype(np.int32)


def cover_exponent(maximum, origin=-20):
    maximum = int(maximum)
    if maximum < 0:
        raise ValueError('negative maximum')
    shift = max(0, maximum.bit_length()-7)
    if maximum > 127 << shift:
        shift += 1
    result = int(origin)+shift
    if not -128 <= result <= 127:
        raise OverflowError('I8 exponent')
    return result


def encode_rows(value, group=128):
    source = bridge(value)
    rows, K = source.shape
    if K % group:
        raise ValueError('unimplemented input tail')
    codes = np.empty(source.shape, dtype=np.int8)
    exponents = np.empty((rows, K//group), dtype=np.int8)
    witnesses = 0
    for row in range(rows):
        for g, start in enumerate(range(0, K, group)):
            values = source[row, start:start+group]
            e = cover_exponent(np.max(abs(values.astype(np.int64))))
            exponents[row, g] = e
            encoded = [rne(v, e+20) for v in values]
            if any(not -127 <= v <= 127 for v in encoded):
                raise AssertionError('dynamic A8 coverage')
            codes[row, start:start+group] = encoded
            for j in (0, group-1):
                want = fraction_rne(Fraction(int(values[j]))*Fraction(2)**(-20-e))
                if want != encoded[j]:
                    raise AssertionError('independent Fraction A8')
                witnesses += 1
    return source, codes, exponents, witnesses


def compile_weights(weights, group=128):
    weights = np.asarray(weights, dtype=np.float32)
    if weights.ndim != 2 or not np.isfinite(weights).all():
        raise ValueError('finite matrix weights required')
    N, K = weights.shape
    if K % group:
        raise ValueError('unimplemented weight tail')
    block = weights.reshape(N, K//group, group)
    maximum = np.max(abs(block), axis=-1).astype(np.float64)
    exponent = np.full(maximum.shape, -30, dtype=np.int16)
    mask = maximum > 0
    exponent[mask] = np.ceil(np.log2(maximum[mask]/127)).astype(np.int16)
    if exponent.min() < -128 or exponent.max() > 127:
        raise OverflowError('offline W exponent')
    codes = np.clip(np.rint(block.astype(np.float64)*np.exp2(-exponent.astype(np.float64))[:, :, None]), -127, 127).astype(np.int8)
    # Fixed endpoints per output/group: Fraction oracle is independent of the
    # FP64 vector compiler; it does not claim every W code was checked by Fraction.
    witnesses = 0
    for n in range(N):
        for g in range(K//group):
            for j in (0, group-1):
                want = max(-127, min(127, fraction_rne(Fraction(float(block[n, g, j]))*Fraction(2)**(-int(exponent[n, g])))))
                if want != int(codes[n, g, j]):
                    raise AssertionError('independent Fraction W8')
                witnesses += 1
    return codes.reshape(N, K), exponent.astype(np.int8), witnesses


def linear(a, ae, w, we, group=128):
    """Actual I32 group matmul, I64 oracle, exact checked mixed-unit sum."""
    rows, K = a.shape; N = len(w); G = K//group
    if K % group or w.shape[1] != K or ae.shape != (rows, G) or we.shape != (N, G):
        raise ValueError('linear group/shape')
    if np.any(abs(a.astype(np.int16)) > 127) or np.any(abs(w.astype(np.int16)) > 127):
        raise ValueError('symmetric S8 format')
    if group*127**2 >= 1 << 31 or K*127**2 << 35 >= 1 << 63:
        raise OverflowError('declared group/full mixed-unit format')
    units = ae.T[:, :, None].astype(np.int16)+we.T[:, None, :].astype(np.int16)
    e0 = units.min(axis=0); delta = units-e0[None]
    if delta.max() > 35:
        raise OverflowError('mixed exponent spread guard35')
    parts = np.empty((G, rows, N), dtype=np.int32)
    acc = np.zeros((rows, N), dtype=np.int64)
    bound = np.zeros_like(acc)
    for g in range(G):
        sl = slice(g*group, (g+1)*group)
        part = a[:, sl].astype(np.int32) @ w[:, sl].astype(np.int32).T
        oracle = a[:, sl].astype(np.int64) @ w[:, sl].astype(np.int64).T
        if not np.array_equal(part, oracle):
            raise AssertionError('full I32 partials vs I64')
        parts[g] = part
        term_bound = np.left_shift(np.full(acc.shape, group*127**2, dtype=np.int64), delta[g])
        bound += term_bound
        acc += np.left_shift(part.astype(np.int64), delta[g])
        if np.any(abs(acc) > bound) or np.any(bound < 0):
            raise OverflowError('checked I64 accumulation')
    sample_columns = sorted({0, min(15, N-1), min(16, N-1), N//2, N-1})
    python_witnesses = 0
    for row in range(rows):
        for col in sample_columns:
            exact = sum(int(parts[g, row, col]) << int(delta[g, row, col]) for g in range(G))
            if checked(exact) != int(acc[row, col]):
                raise AssertionError('arbitrary integer complete reduction')
            python_witnesses += 1
    return {'A8': a, 'Ae': ae, 'parts': parts, 'units': units, 'acc': acc, 'e0': e0}, {
        'INT64_partial_values_checked': int(parts.size), 'Python_complete_reduction_witnesses': python_witnesses,
        'group': group, 'groups': G, 'I32_group_bound': group*127**2,
        'observed_acc_abs_max': int(np.max(abs(acc))), 'format_bound_max': int(bound.max()),
        'exponent_spread_max': int(delta.max()), 'MACs': rows*N*K,
        'scope': 'I32 group dot/I64 exact mixed scale; no intermediate RQ, no target timing'}


def output_base(calibration):
    if not np.isfinite(calibration).all():
        raise ValueError('finite calibration required')
    maximum = 2*np.max(abs(np.asarray(calibration, dtype=np.float64)), axis=0)
    e = np.full(maximum.shape, -30, dtype=np.int16)
    mask = maximum > 0; e[mask] = np.ceil(np.log2(maximum[mask]/127)).astype(np.int16)
    if e.min() < -128 or e.max() > 127:
        raise OverflowError('Y base exponent')
    return e.astype(np.int8)


def quant_output(acc, units, out_units, bits):
    lo, hi = (-128, 127) if bits == 8 else (-32768, 32512)
    codes = np.empty(acc.shape, dtype=np.int8 if bits == 8 else np.int16)
    saturation = 0
    for row, col in np.ndindex(acc.shape):
        shift = int(out_units[row, col])-int(units[row, col])
        value = rne(acc[row, col], shift)
        want = fraction_rne(Fraction(int(acc[row, col]))*Fraction(2)**(-shift))
        if value != want:
            raise AssertionError('Fraction complete output RNE')
        saturation += not lo <= value <= hi
        codes[row, col] = max(lo, min(hi, value))
    return codes, {'saturation': saturation, 'Fraction_output_codes': int(codes.size)}


def delta_tiles(acc, units, base, tile=16):
    if acc.shape[1] % tile:
        raise ValueError('unimplemented output tile tail')
    delta = np.empty((len(acc), acc.shape[1]//tile), dtype=np.int8)
    trials = terms = 0
    for row in range(len(acc)):
        for t, start in enumerate(range(0, acc.shape[1], tile)):
            sl = slice(start, start+tile)
            if not np.any(acc[row, sl]):
                delta[row, t] = 0; continue
            for d in range(-16, 17):
                trials += 1; terms += tile
                values = [rne(v, int(e)+d-int(u)) for v, e, u in zip(acc[row, sl], base[sl], units[row, sl])]
                if all(-128 <= v <= 127 for v in values):
                    delta[row, t] = d; break
            else:
                raise OverflowError('tile delta outside frozen[-16,16]')
    return delta, {'delta_search_trials': trials, 'delta_RNE_compare_terms': terms}


def convert_k128(codes, units, group=128):
    """Integer common-unit conversion before residual, preserving all base units."""
    rows, H = codes.shape
    if H % group:
        raise ValueError('unimplemented K128 tail')
    result = np.empty_like(codes, dtype=np.int8); exponents = np.empty((rows, H//group), dtype=np.int8)
    fractions = 0; shifts = 0
    for row in range(rows):
        for g, start in enumerate(range(0, H, group)):
            sl = slice(start, start+group); e0 = int(units[row, sl].min())
            aligned = [checked(int(v) << int(u-e0)) for v, u in zip(codes[row, sl], units[row, sl])]
            e = cover_exponent(max(abs(v) for v in aligned), origin=e0)
            exponents[row, g] = e
            for j, value in enumerate(aligned):
                q = rne(value, e-e0)
                expected = fraction_rne(Fraction(int(codes[row, start+j]))*Fraction(2)**(int(units[row, start+j])-e))
                if q != expected or not -127 <= q <= 127:
                    raise AssertionError('K128 Fraction/coverage')
                result[row, start+j] = q; fractions += 1; shifts += 1
    return result, np.repeat(exponents, group, axis=1), exponents, {
        'K128_alignment_and_RNE_values': shifts, 'Fraction_K128_conversion_values': fractions,
        'K128_exponent_bytes': int(exponents.nbytes), 'K128_S64_scan_read_write_values': 2*int(codes.size)}


def residual_add(codes, units, residual):
    r32 = bridge(residual)
    common = np.minimum(units, -20).astype(np.int16)
    result = np.empty(codes.shape, dtype=np.int64)
    for index in np.ndindex(codes.shape):
        e = int(common[index]); d = int(units[index])
        left = checked(int(codes[index]) << (d-e))
        right = checked(int(r32[index]) << (-20-e))
        value = checked(left+right)
        independent = Fraction(int(codes[index]))*Fraction(2)**d+Fraction(int(r32[index]), 1 << 20)
        if Fraction(value)*Fraction(2)**e != independent:
            raise AssertionError('Fraction residual complete alignment/add')
        result[index] = value
    return r32, result, common, {'Fraction_residual_add_values': int(result.size),
                               'S64_align_add_values': int(result.size), 'residual_bridge_max_abs': error(physical(r32, -20), residual)['max_abs']}


def rms_float(value, raw_weight, epsilon=1e-6):
    """Explicit FP32 full-hidden bridge matching Q35's effective1+weight."""
    value = np.asarray(value, dtype=np.float32)
    variance = np.mean(value*value, axis=-1, keepdims=True, dtype=np.float32)
    inv = np.reciprocal(np.sqrt(variance+np.float32(epsilon)))
    return ((value*inv)*(np.asarray(raw_weight, dtype=np.float32)+np.float32(1))).astype(np.float32)


def packets(payload):
    return sum(64+64*((min(1984, payload-start)+63)//64) for start in range(0, payload, 1984))


def cost(H, K, N, rows, profile, codes, units, delta, stats):
    width = codes.dtype.itemsize; tiles = H//16; groups = H//128
    dynamic = profile in ('tile16_delta_ACT8', 'delta_to_K128_ACT8')
    incoming_dynamic_bytes = rows*tiles if dynamic else 0
    outgoing_extra = groups if profile == 'delta_to_K128_ACT8' else tiles if dynamic else 0
    explicit_packet = sum(packets(H*width+32+outgoing_extra) for _ in range(rows))
    return {'rows': rows, 'complete_hidden_channels': H, 'next_projection_selected_outputs': N,
            'source_down_full_K': K, 'ACT_payload_bytes': int(codes.nbytes),
            'static_base_exponent_bytes': H, 'incoming_tile16_delta_bytes': incoming_dynamic_bytes,
            'outgoing_scale_metadata_bytes': rows*outgoing_extra,
            'complete_row_packet_bytes_static_base_resident': explicit_packet,
            'packet_contract': 'each row separately,64B header,32B coordinates,64B payload alignment,max1984B fragments; base scale resident and its initial transfer counted separately',
            'initial_base_scale_wire_bytes': packets(H),
            'original_outlet_per16output_tile_packet_bytes_explicit_scale': sum(packets(16*width+16+32+(1 if dynamic else 0)) for _ in range(rows*tiles)),
            'one_row_exact_residual_S64_plus_I16_units_bytes': H*10,
            'one_row_F32_norm_buffer_bytes': H*4, 'F32_norm_gamma_bytes': H*4,
            'norm_V16KiB_capacity': {'exact_sum_and_units_fit': H*10 <= 16384,
                                    'one_inplace_F32_row_fits': H*4 <= 16384,
                                    'row_and_gamma_simultaneously_fit': H*8 <= 16384},
            'norm_float_boundary_cost': 'FP32 conversion,full hidden sum-of-squares/rsqrt/gamma remain floating; integer hardware implementation/cycles pending; in-place two-pass or spill/gamma reads must be scheduled',
            'single128bit_1RW_bank_lower_bound_beats': {'ACT_write_read': 2*((H*width+15)//16)*rows,
                                                       'wide_sum_write_read': 2*((H*8+15)//16)*rows,
                                                       'unit_write_read': 2*((H*2+15)//16)*rows,
                                                       'norm_gamma_read': ((H*4+15)//16)*rows},
            'down_W8_total_bytes': H*K, 'down_W128_exponent_total_bytes': H*(K//128),
            'one16output_down_W128_scale_bytes': 16*(K//128),
            'one16output_fixed_W_L1_U32_certificate_bytes_if_used': 16*(K//128)*4,
            'next_projection_W8_bytes': N*H, 'next_projection_W128_scale_bytes': N*groups,
            'next_projection_input': 'fresh A8K128 after explicit FP32 norm bridge; same W8K128 acrossvariants; do not mechanically charge3 products solely because prenorm ACT was16bit',
            'scope': 'logical sizes and physical packet/1RW lower bounds, no finite scheduler,RTL or PPA',
            'integer_work': stats}


def verify_capture(directory):
    manifest = json.loads((directory/'manifest.json').read_text())
    if manifest.get('sealed_reserved') or manifest['model']['id'] != 'Qwen/Qwen3.5-4B' or manifest['status'] != 'PASS':
        raise ValueError('expected nonreserved accepted Q35 capture')
    for name, expected in manifest['artifacts'].items():
        path = (directory/name).resolve()
        if not path.is_relative_to(directory.resolve()) or sha(path) != expected['sha256'] or path.stat().st_size != expected['bytes']:
            raise ValueError('capture SHA/size/path '+name)
    filename = manifest.get('consumer_artifact', 'consumer-raw.npz')
    if filename not in manifest['artifacts']:
        raise ValueError('consumer artifact must be indexed')
    return manifest, directory/filename


def source(binding_path):
    b = json.loads(binding_path.read_text()) if binding_path else {}
    code_sha = sha(__file__)
    if b and b.get('consumer_sha256') != code_sha:
        raise ValueError('consumer source binding')
    try:
        commit = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=Path(__file__).parent, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = b.get('commit', 'unverified')
    if b.get('commit') and commit != b['commit']:
        raise ValueError('source commit binding')
    return {'commit': commit, 'consumer_sha256': code_sha, 'binding': b}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input', type=Path, required=True); p.add_argument('--out', type=Path, required=True)
    p.add_argument('--binding', type=Path)
    a = p.parse_args()
    if a.out.exists():
        raise ValueError('refuse existing output')
    bound_source = source(a.binding)
    captured, filename = verify_capture(a.input)
    with np.load(filename, allow_pickle=False) as loaded:
        data = {name: loaded[name] for name in loaded.files}
    down_w, norm_w, next_w = (data['weight.'+key] for key in ('down', 'next_norm', 'next_projection'))
    H, K = down_w.shape; N = len(next_w)
    if (H, K, next_w.shape, norm_w.shape) != (2560, 9216, (16, 2560), (2560,)):
        raise ValueError('frozen complete-hidden Q35/selected16 projection shape')
    chain = captured['chain']
    if chain['from_layer'] != 3 or chain['to_layer'] != 4 or chain['down_bias'] or chain['next_projection_bias']:
        raise ValueError('frozen actual layer/bias topology')
    epsilon = float(chain['norm_epsilon'])
    if epsilon != 1e-6:
        raise ValueError('frozen Q35 epsilon')
    # Reference chain validation is independent of candidate rounding choices.
    capture_checks = {}
    for case, count in [('calibration', 16), ('prefill', 8), ('decode', 32)]:
        if data[case+'.A'].shape != (count, K) or data[case+'.rows'].shape != (count,):
            raise ValueError('frozen row selection '+case)
        for field in ['down', 'residual', 'sum', 'norm']:
            if data[case+'.'+field].shape != (count, H):
                raise ValueError('complete hidden required '+case+'.'+field)
        if data[case+'.projection'].shape != (count, N):
            raise ValueError('selected actual projection outputs '+case)
        if len(np.unique(data[case+'.rows'])) != count or data[case+'.rows'].min() < 0:
            raise ValueError('unique absolute selected rows '+case)
        checks = {'down': error(data[case+'.A']@down_w.T, data[case+'.down']),
                  'sum': error(data[case+'.down']+data[case+'.residual'], data[case+'.sum']),
                  'norm': error(rms_float(data[case+'.sum'], norm_w, epsilon), data[case+'.norm']),
                  'projection': error(data[case+'.norm']@next_w.T, data[case+'.projection'])}
        if any(v['relative_rmse'] > 1e-5 or v['max_abs'] > 2e-3 for v in checks.values()):
            raise ValueError('captured native chain binding failed '+case+' '+json.dumps(checks))
        capture_checks[case] = checks
    a.out.mkdir(parents=True); start = time.monotonic()
    qw, ew, dwitness = compile_weights(down_w); nw, ne, nwitness = compile_weights(next_w)
    base = output_base(data['calibration.down']); next_base = output_base(data['calibration.projection'])
    common = {'down.W8': qw, 'down.We': ew, 'next.W8': nw, 'next.We': ne, 'down.Ybase': base,
              'next.Ybase': next_base, 'next.raw_norm_weight': norm_w}
    reports = []
    for case in ['prefill', 'decode']:
        rows = len(data[case+'.A'])
        down_source, aa, ae, awitness = encode_rows(data[case+'.A'])
        down, downstats = linear(aa, ae, qw, ew)
        for name, value in down.items(): common[case+'.down.'+name] = value
        common[case+'.down.source_S32Q20'] = down_source
        for name in ['down', 'residual', 'sum', 'norm', 'projection', 'rows']:
            common[case+'.reference.'+name] = data[case+'.'+name]
        d, dstats = delta_tiles(down['acc'], down['e0'], base)
        upstream = physical(down['acc'], down['e0'])
        # Baseline next W8A8 error uses the actual captured native norm output.
        _, oracle_a, oracle_ae, _ = encode_rows(data[case+'.norm'])
        next_oracle, next_oracle_stats = linear(oracle_a, oracle_ae, nw, ne)
        for name, value in next_oracle.items(): common[case+'.native_norm_projection.'+name] = value
        next_oracle_real = physical(next_oracle['acc'], next_oracle['e0'])
        # Upper numeric reference for outlet RQ alone: no ACT format yet.
        pre_sum = (upstream+physical(bridge(data[case+'.residual']), -20)).astype(np.float32)
        pre_norm = rms_float(pre_sum, norm_w, epsilon)
        _, pre_a, pre_ae, _ = encode_rows(pre_norm)
        pre_projection, _ = linear(pre_a, pre_ae, nw, ne)
        common[case+'.pre_outlet.sum_F32_bridge'] = pre_sum
        common[case+'.pre_outlet.norm_F32_bridge'] = pre_norm
        for name, value in pre_projection.items(): common[case+'.pre_outlet.next.'+name] = value
        pre_projection_real = physical(pre_projection['acc'], pre_projection['e0'])
        for profile in PROFILES:
            bits = 16 if profile == 'same_range_ACT16' else 8
            unit = np.broadcast_to(base.astype(np.int16)[None], down['acc'].shape).copy()
            if bits == 16: unit -= 8
            if profile in ('tile16_delta_ACT8', 'delta_to_K128_ACT8'):
                unit += np.repeat(d.astype(np.int16), 16, axis=1)
            codes, qstats = quant_output(down['acc'], down['e0'], unit, bits)
            outgoing_codes, outgoing_units = codes, unit
            kexponents = np.empty((rows, 0), dtype=np.int8); kstats = {}
            if profile == 'delta_to_K128_ACT8':
                outgoing_codes, outgoing_units, kexponents, kstats = convert_k128(codes, unit)
            r32, summed, sum_unit, rstats = residual_add(outgoing_codes, outgoing_units, data[case+'.residual'])
            sum_f32 = physical(summed, sum_unit).astype(np.float32)
            norm = rms_float(sum_f32, norm_w, epsilon)
            norm_source, norm_a, norm_ae, norm_witness = encode_rows(norm)
            nxt, nextstats = linear(norm_a, norm_ae, nw, ne)
            final_units = np.broadcast_to(next_base.astype(np.int16)[None], nxt['acc'].shape)
            final_codes, finalstats = quant_output(nxt['acc'], nxt['e0'], final_units, 8)
            nxt_real = physical(nxt['acc'], nxt['e0'])
            arrays = {'outlet_codes': codes, 'outlet_units': unit, 'outlet_delta': d if 'delta' in profile else np.empty((rows, 0), dtype=np.int8),
                      'transport_codes': outgoing_codes, 'transport_units': outgoing_units, 'K128_exponents': kexponents,
                      'residual_S32Q20': r32, 'sum_acc64': summed, 'sum_units': sum_unit,
                      'sum_F32_bridge': sum_f32, 'norm_F32_bridge': norm, 'norm_source_S32Q20': norm_source,
                      'next.A8': norm_a, 'next.Ae': norm_ae, 'next.parts': nxt['parts'], 'next.units': nxt['units'],
                      'next.acc': nxt['acc'], 'next.e0': nxt['e0'], 'next.final_ACT8': final_codes,
                      'next.final_units': final_units}
            npz(a.out/(case+'.'+profile+'.npz'), arrays)
            stats = {**qstats, **rstats, **kstats, **(dstats if 'delta' in profile else {})}
            reports.append({'case': case, 'profile': profile, 'rows': rows, 'hidden': H, 'next_selected_outputs': N,
                            'upstream_down_before_outlet_RQ_vs_native': error(upstream, data[case+'.down']),
                            'down_after_outlet_RQ_vs_native': error(physical(codes, unit), data[case+'.down']),
                            'transport_requant_vs_outlet': error(physical(outgoing_codes, outgoing_units), physical(codes, unit)),
                            'sum_vs_native': error(sum_f32, data[case+'.sum']), 'norm_vs_native': error(norm, data[case+'.norm']),
                            'next_projection_vs_native': error(nxt_real, data[case+'.projection']),
                            'next_projection_vs_native_norm_same_W8A8': error(nxt_real, next_oracle_real),
                            'next_projection_vs_upstream_no_outlet_RQ': error(nxt_real, pre_projection_real),
                            'native_norm_W8A8_vs_native_projection': error(next_oracle_real, data[case+'.projection']),
                            'next_final_ACT8_vs_native': error(physical(final_codes, final_units), data[case+'.projection']),
                            'down_integer': downstats, 'next_integer': nextstats,
                            'next_final_RQ': finalstats, 'input_A_Fraction_witnesses': awitness,
                            'norm_A_Fraction_witnesses': norm_witness,
                            'costs': cost(H, K, N, rows, profile, outgoing_codes, outgoing_units, d, stats),
                            'integer_norm_implemented': False, 'complete_next8192_projection': False,
                            'full_model_quality_accepted': False, 'hardware_performance_accepted': False})
    npz(a.out/'common.npz', common); save(a.out/'consumer.json', reports)
    save(a.out/'manifest.json', {'status': 'PASS', 'source': bound_source, 'input_manifest_sha256': sha(a.input/'manifest.json'),
                               'input_artifact_sha256': sha(filename), 'model': captured['model'],
                               'capture_chain_checks': capture_checks, 'conditions': len(reports),
                               'weight_Fraction_endpoint_witnesses': {'down': dwitness, 'next': nwitness},
                               'seconds': time.monotonic()-start, 'environment': {'python': platform.python_version(), 'numpy': np.__version__},
                               'scope': __doc__, 'topology': 'layer3.mlp.down_proj -> complete hidden residual -> layer4.input_layernorm(1+weight,eps1e-6) -> layer4.linear_attn.in_proj_qkv[:16] (Q prefix, not whole GDN)',
                               'profiles': PROFILES, 'float_boundaries': ['original native FP32 down input/residual', 'offline FP64 W/Y compilers', 'FP32 complete-hidden RMSNorm and dequant conversion', 'FP32 norm -> S32Q20 bridge; numerical metrics'],
                               'scale_contract': 'base eY per output channel; delta per16-output tile/row, so even within a tile units need not be equal; K128 conversion is explicit before residual; norm then publishes newly quantized A8K128',
                               'evidence_limits': ['previously selected short diagnostic positions, no application quality acceptance', 'not all-integer norm/model or full next8192 projection/GDN', 'logical traffic/1RW lower bounds, not finite schedule/RTL/PPA'],
                               'artifacts': {f.name: {'bytes': f.stat().st_size, 'sha256': sha(f)} for f in sorted(a.out.iterdir()) if f.is_file()}})
    print(json.dumps({'status': 'PASS', 'conditions': len(reports), 'hidden': H, 'next_selected_outputs': N}), flush=True)


if __name__ == '__main__':
    main()
