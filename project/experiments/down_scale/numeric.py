"""Candidate dyadic W8A8, checked mixed-scale accumulation, one final RNE.

Float operations are limited to the capture bridge, offline compiler and error
measurement. Dynamic scales and every subsequent arithmetic step use integers.
This is an executable reference, not a fast INT8 kernel.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from common import config, save, npz, provenance, manifest, checked_manifest, digest


def check(value, bits):
    value = int(value)
    if not -(1 << (bits-1)) <= value < (1 << (bits-1)): raise OverflowError('i'+str(bits))
    return value


def shift_rne(value, shift):
    value, shift = int(value), int(shift)
    if shift < -63 or shift > 63: raise ValueError('shift domain')
    if shift <= 0: return value << -shift
    q, r = divmod(abs(value), 1 << shift)
    q += r > (1 << (shift-1)) or (r == (1 << (shift-1)) and q % 2 == 1)
    return -q if value < 0 else q


def exponent_float(x):
    m = float(np.max(abs(np.asarray(x, dtype=np.float64))))
    return -30 if m == 0 else int(np.ceil(np.log2(m/127)))


def exponent_integer(x):
    """Smallest e >= -20 whose 127*2**e covers S32Q20 max; no log/div."""
    m = int(np.max(abs(np.asarray(x, dtype=np.int64))))
    s = 0
    while m > (127 << s): s += 1
    return -20+s


def encode_source(x, e):
    """Vectorized exact signed RNE shift; input checked S32, output [-127,127]."""
    s = int(e)+20
    if s < 0 or s > 43: raise ValueError('source quantization shift')
    x = np.asarray(x, dtype=np.int64); mag = abs(x)
    if s:
        q = mag >> s; rem = mag & ((1 << s)-1)
        q += (rem > (1 << (s-1))) | ((rem == (1 << (s-1))) & ((q & 1) == 1))
    else: q = mag.copy()
    q = np.where(x < 0, -q, q)
    return np.clip(q, -127, 127).astype(np.int8), int(np.count_nonzero(abs(q) > 127))


def compile_static(cal, group, objective):
    cfg = config(); result = []
    for start in range(0, cal.shape[1], group):
        x = cal[:, start:start+group]
        e = max(-20, exponent_integer(x))
        if objective == 'mse':
            options = []
            for off in cfg['mse_exponent_offsets']:
                candidate = max(-20, e+off); codes, _ = encode_source(x, candidate)
                err = codes.astype(np.float64)*2.**candidate-x.astype(np.float64)*2.**-20
                options.append((float(np.mean(err**2)), candidate))
            # Equal MSE chooses smaller step (deterministic, calibration only).
            e = min(options)[1]
        result.append(e)
    return np.array(result, dtype=np.int8)


def profiles():
    cfg = config(); result = []
    for cal in cfg['static_calibration_sets']:
        for objective in cfg['static_objectives']:
            for ag in [8192, cfg['static_A_group']]:
                result.append(dict(mode='static', cal=cal, objective=objective, ag=ag))
    result += [dict(mode='dynamic', cal='none', objective='max', ag=g) for g in [8192, *cfg['dynamic_A_groups']]]
    return [{**p, 'wg': wg, 'name': '_'.join(map(str, [p['mode'], p['cal'], p['objective'], p['ag'], wg]))}
            for p in result for wg in cfg['W_granularities']]


def compile_weights(w, group):
    ew = np.empty((len(w), w.shape[1]//group), dtype=np.int8); qw = np.empty(w.shape, dtype=np.int8)
    for j in range(len(w)):
        for g, start in enumerate(range(0, w.shape[1], group)):
            e = exponent_float(w[j, start:start+group]); ew[j, g] = e
            qw[j, start:start+group] = np.clip(np.rint(w[j, start:start+group].astype(np.float64)/2.**e), -127, 127).astype(np.int8)
    return ew, qw


def quantize(x, profile, static=None):
    group = profile['ag']; ea = np.empty((len(x), x.shape[1]//group), dtype=np.int8)
    qa = np.empty(x.shape, dtype=np.int8); clipped = 0
    for i in range(len(x)):
        for g, start in enumerate(range(0, x.shape[1], group)):
            e = int(static[g]) if static is not None else exponent_integer(x[i, start:start+group])
            ea[i, g] = e; qa[i, start:start+group], n = encode_source(x[i, start:start+group], e); clipped += n
    return ea, qa, clipped


def calculate(qa, qw, ea, ew, ey, ag, wg):
    rows, k = qa.shape; n = len(qw); group = min(ag, wg); groups = k//group
    parts = np.empty((groups, rows, n), dtype=np.int32)
    units = np.empty(parts.shape, dtype=np.int16)
    for g in range(groups):
        start = g*group
        part = qa[:, start:start+group].astype(np.int32) @ qw[:, start:start+group].astype(np.int32).T
        if np.max(abs(part.astype(np.int64))) > group*127**2 or group*127**2 >= 2**31: raise OverflowError('partial i32')
        parts[g] = part; units[g] = ea[:, start//ag, None].astype(np.int16)+ew[:, start//wg][None, :].astype(np.int16)
    e0 = np.min(units, axis=0); accum = np.empty((rows, n), dtype=np.int64)
    output = np.empty((rows, n), dtype=np.int8); early = np.empty(output.shape, dtype=np.int8)
    max_bound = max_observed = max_spread = sat = mismatches = 0
    max_required_bits = 0
    for idx in np.ndindex(accum.shape):
        exact = 0; bound = 0; early_sum = 0
        for g in range(groups):
            delta = int(units[(g,)+idx])-int(e0[idx]); max_spread = max(max_spread, delta)
            exact = check(exact + (int(parts[(g,)+idx]) << delta), 64)
            bound += group*127**2 << delta
            early_sum += max(-128, min(127, shift_rne(parts[(g,)+idx], int(ey[idx[1]])-int(units[(g,)+idx]))))
        check(bound, 64)  # format-wide bound, not only observed safety
        max_bound = max(max_bound, bound); max_observed = max(max_observed, abs(exact))
        max_required_bits = max(max_required_bits, bound.bit_length()+1)
        accum[idx] = exact; out = shift_rne(exact, int(ey[idx[1]])-int(e0[idx]))
        sat += not -128 <= out <= 127; output[idx] = max(-128, min(127, out))
        early[idx] = max(-128, min(127, early_sum)); mismatches += output[idx] != early[idx]
    return dict(parts=parts, units=units, e0=e0, acc=accum, out=output), {
        'group': group, 'groups': groups, 'partial_i32_bound': group*127**2,
        'observed_max_abs_aligned_acc': max_observed, 'worst_aligned_bound': max_bound,
        'required_signed_bits_for_this_scale_matrix': max_required_bits, 'max_scale_exponent_spread': max_spread,
        'output_saturation_count': int(sat), 'early_group_RQ_mismatches': int(mismatches)}


def metrics(y, ref):
    diff = np.asarray(y, dtype=np.float64)-ref.astype(np.float64)
    return {'relative_rmse': float(np.sqrt(np.mean(diff**2))/max(np.sqrt(np.mean(ref.astype(np.float64)**2)), 1e-30)),
            'max_abs': float(np.max(abs(diff)))}


def main():
    p = argparse.ArgumentParser(); p.add_argument('--capture', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True); p.add_argument('--development', action='store_true'); a = p.parse_args()
    if a.output.exists(): raise ValueError('refuse overwrite')
    prod = provenance(a.development); checked_manifest(a.capture); cfg = config()
    data = np.load(a.capture/'capture.npz', allow_pickle=False)
    source = {}; bridge = {}
    for key in data.files:
        if key.endswith('.A'):
            raw = np.rint(data[key].astype(np.float64)*2.**20)
            if not np.isfinite(raw).all() or np.max(abs(raw)) >= 2**31: raise OverflowError('S32Q20 bridge')
            source[key[:-2]] = raw.astype(np.int32)
            bridge[key] = metrics(raw*2.**-20, data[key])
    original = source['calibration']; expanded = np.concatenate([original, *[source[n] for n in cfg['new_calibration_texts']]])
    calibration = {'original32': original, 'expanded128': expanded}
    w = data['W']; ey = np.array([exponent_float(2*data['calibration.Y'][:, j]) for j in range(16)], dtype=np.int8)
    reports = []; arrays = {'Y_e': ey}; parameters = []; wc = {}
    for pr in profiles():
        if pr['wg'] not in wc: wc[pr['wg']] = compile_weights(w, pr['wg'])
        ew, qw = wc[pr['wg']]; tag = pr['name']; arrays[tag+'.W_i8'] = qw; arrays[tag+'.W_e'] = ew
        se = compile_static(calibration[pr['cal']], pr['ag'], pr['objective']) if pr['mode'] == 'static' else None
        if se is not None: arrays[tag+'.static_A_e'] = se
        parameters.append({**pr, 'static_A_e': se.tolist() if se is not None else None})
        for text in ['systems', 'arithmetic', 'heldout']:
            for phase, sl in [('prefill', slice(0,32)), ('decode', slice(32,40))]:
                key = tag+'.'+text+'.'+phase; x = source[text][sl]; ref = data[text+'.Y'][sl]
                ea, qa, clip = quantize(x, pr, se)
                result, stats = calculate(qa, qw, ea, ew, ey, pr['ag'], pr['wg'])
                before = result['acc'].astype(np.float64)*np.exp2(result['e0'].astype(np.float64))
                after = result['out'].astype(np.float64)*np.exp2(ey.astype(np.float64))[None, :]
                record = {'key': key, 'profile': tag, 'text': text, 'phase': phase, 'shape_A': list(x.shape),
                    'source_zero_fraction': float(np.mean(x==0)), 'A_zero_fraction': float(np.mean(qa==0)),
                    'A_clip_count': clip, 'before_final_RQ': metrics(before, ref), 'after_final_RQ': metrics(after, ref), **stats}
                reports.append(record)
                for field, value in {'A_i8': qa, 'A_e': ea, **result}.items(): arrays[key+'.'+field] = value
    a.output.mkdir(parents=True)
    save(a.output/'profiles.json', parameters); save(a.output/'numeric.json', reports)
    save(a.output/'bridge.json', bridge); npz(a.output/'integers.npz', arrays)
    save(a.output/'summary.json', {'cases': len(reports), 'profiles': [
        {'name': p['name'], 'max_rmse': max(r['after_final_RQ']['relative_rmse'] for r in reports if r['profile']==p['name']),
         'max_heldout_rmse': max(r['after_final_RQ']['relative_rmse'] for r in reports if r['profile']==p['name'] and r['text']=='heldout'),
         'max_required_bits': max(r['required_signed_bits_for_this_scale_matrix'] for r in reports if r['profile']==p['name']),
         'local_screen_passed': all(r['after_final_RQ']['relative_rmse'] <= cfg['exploratory_numerical_gate']['max_case_relative_rmse'] and
             r['output_saturation_count']/np.prod(r['shape_A'][:1]+[16]) <= cfg['exploratory_numerical_gate']['output_saturation_fraction']
             for r in reports if r['profile']==p['name'])} for p in parameters]})
    manifest(a.output, prod, status='PASS', capture_sha256=digest(a.capture/'manifest.json'),
        scope=cfg['scope'], float_boundary='FP32 nonlinear capture -> offline S32Q20 bridge; offline W/static/Y compiler; integer dynamic scales and arithmetic afterward')
    print(json.dumps({'cases': len(reports), 'profiles': len(parameters), 'status': 'PASS'}))


if __name__ == '__main__': main()
