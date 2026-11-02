"""Independent stdlib checks for the real Qwen F integer RTL expectations.

Execute only in the root-owned server qrtl Slurm workflow. No RTL is started
by this program. It never consults C++ raw accumulators or DUT outputs.
M verification is explicitly sampled: eight full-K dots per matrix per row.
N/G/E are checked at their complete H1024/I3072 dimensions.
"""
import argparse
import array
import hashlib
import importlib.util
import json
import math
import re
import sys
from fractions import Fraction
from pathlib import Path

REFERENCE_DEPENDENCIES = [
    'work/Melodydt/151/f16_integer_reference.py',
    'project/rtl/block_v2/block_v2_g_tables.svh',
]
MATRIX_NAMES = {
    'gate': 'model.layers.0.mlp.gate_proj.weight',
    'up': 'model.layers.0.mlp.up_proj.weight',
    'down': 'model.layers.0.mlp.down_proj.weight',
}
POST_GAMMA = 'model.layers.0.post_attention_layernorm.weight'
SAMPLES = {
    'gate': [0, 1, 7, 63, 250, 251, 1536, 3071],
    'up': [0, 1, 7, 63, 250, 251, 1536, 3071],
    'down': [0, 1, 7, 127, 250, 251, 511, 1023],
}


def sha(path):
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            digest.update(block)
    return digest.hexdigest()


def inside(base, relative):
    path = (base / relative).resolve()
    if path != base and base not in path.parents:
        raise ValueError('numeric artifact path escapes numeric directory')
    return path


class Audit:
    def __init__(self):
        self.checks = 0

    def need(self, condition, message):
        self.checks += 1
        if not condition:
            raise AssertionError(message)


def clip16(value):
    return max(-32768, min(32767, value))


def quant16(values, frac):
    result = []
    clipped = 0
    scale = 1 << frac
    for value in values:
        if not math.isfinite(value):
            raise ValueError('nonfinite actual FP32 input')
        # Actual F32/BF16 floats are exact dyadic values in Python binary64.
        rounded = round(Fraction.from_float(float(value)) * scale)
        narrowed = clip16(rounded)
        clipped += rounded != narrowed
        result.append(narrowed)
    return result, clipped


def f32(path):
    result = array.array('f')
    result.frombytes(path.read_bytes())
    return result


def read_hex(path, words, audit):
    lines = path.read_text(encoding='ascii').splitlines()
    audit.need(len(lines) == words, 'hex word count: ' + str(path))
    result = []
    for line in lines:
        audit.need(bool(re.fullmatch(r'[0-9a-fA-F]{32}', line)), 'hex128 record: ' + str(path))
        word = int(line, 16)
        for lane in range(8):
            code = (word >> (16 * lane)) & 0xffff
            result.append(code - 65536 if code >= 32768 else code)
    return result


def load_g_reference(repo, audit):
    reference = repo / REFERENCE_DEPENDENCIES[0]
    table = repo / REFERENCE_DEPENDENCIES[1]
    spec = importlib.util.spec_from_file_location('qnum_independent_f16_math', str(reference))
    module = importlib.util.module_from_spec(spec)
    # Execute the frozen reference in memory; never create source-tree bytecode.
    exec(compile(reference.read_bytes(), str(reference), 'exec'), module.__dict__)
    validation = module.validate_native_table(table.read_text(encoding='utf-8'))
    audit.need(validation['equal_all_nodes'], 'independent G mathematics versus native table')
    audit.need(len(module.MATH_TABLES[0]) == 513, 'SiLU native node count')
    return module, validation


def canonical_stream(weights, expected, stream_path, audit):
    digest = hashlib.sha256()
    count = 0
    requests = 0

    def chunk(matrix, group, kchunk, K):
        raw = weights[matrix]
        payload = b''.join(
            raw[(group * 8 + n) * K + kchunk * 32 + tile * 8:
                (group * 8 + n) * K + kchunk * 32 + tile * 8 + 8]
            for tile in range(4) for n in range(8))
        if len(payload) != 256:
            raise ValueError('truncated row-major matrix while rebuilding canonical chunk')
        return payload

    for group in range(384):
        for matrix in ['gate', 'up']:
            for kchunk in range(32):
                payload = chunk(matrix, group, kchunk, 1024)
                digest.update(payload)
                count += len(payload)
                requests += 1
    for group in range(128):
        for kchunk in range(96):
            payload = chunk('down', group, kchunk, 3072)
            digest.update(payload)
            count += len(payload)
            requests += 1
    actual_hash = sha(stream_path)
    audit.need(count == 9437184 and requests == 36864, 'complete native weight request domain')
    audit.need(stream_path.stat().st_size == count == expected['weights_stream_bytes'], 'canonical stream byte count')
    audit.need(digest.hexdigest() == actual_hash == expected['weights_stream_sha256'], 'independent source-S8/read-order stream SHA')
    return {'bytes': count, 'requests': requests, 'beats': requests * 16,
            'sha256': actual_hash, 'source_order_rebuilt_independently': True}


def perform(args, report):
    repo = args.root.resolve()
    numeric = args.numeric_dir.resolve()
    audit = Audit()
    audit.need(sys.byteorder == 'little', 'little-endian data ABI')
    audit.need(hasattr(math, 'isqrt'), 'server Python with math.isqrt required')
    index_path = numeric / 'rtl-fixture-index.json'
    index = json.loads(index_path.read_text(encoding='utf-8'))
    receipt_path = numeric / 'numeric-run-receipt.json'
    receipt = json.loads(receipt_path.read_text(encoding='utf-8'))
    summary_path = numeric / 'numeric-summary.json'
    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    audit.need(receipt['status'] == 'PASS_SELECTED_LAYER0_NUMERICAL_DIAGNOSTIC_NOT_RTL_OR_FULL_MODEL_QUALITY', 'successful source numerical run')
    audit.need(receipt['revision'] == 'c1899de289a04d12100db370d81485cdf75e47ca', 'pinned checkpoint revision')
    audit.need(receipt['repo'] == 'Qwen/Qwen3-0.6B', 'checkpoint repository')
    report['source_numeric_receipt_sha256'] = sha(receipt_path)
    report['fixture_index_sha256'] = sha(index_path)
    report['summary_sha256'] = sha(summary_path)
    report['dependencies'] = [{'path': p, 'sha256': sha(repo / p)} for p in REFERENCE_DEPENDENCIES]
    gref, table_validation = load_g_reference(repo, audit)
    report['G_table_validation'] = dict(table_validation, native_fn0_nodes=513)
    declared_outputs = {entry['path']: entry for entry in receipt['outputs']}

    def artifact(path):
        relative = str(path.relative_to(numeric)).replace('\\', '/')
        audit.need(relative in declared_outputs, 'artifact missing numerical receipt: ' + relative)
        expected = declared_outputs[relative]
        audit.need(path.stat().st_size == expected['bytes'], 'receipt artifact byte size: ' + relative)
        audit.need(sha(path) == expected['sha256'], 'receipt artifact SHA: ' + relative)

    artifact(index_path)
    artifact(summary_path)
    artifact(numeric / 'tensor-map.tsv')

    # Resolve exactly the task's four checkpoint tensors, not arbitrary commands.
    tensor_paths = {}
    for line in (numeric / 'tensor-map.tsv').read_text(encoding='utf-8').splitlines():
        fields = line.split('\t')
        audit.need(len(fields) == 4, 'tensor TSV record')
        tensor_paths[fields[0]] = (Path(fields[1]).resolve(), int(fields[2]), int(fields[3]))
    inputs = {entry['name']: entry for entry in receipt['inputs']}
    gamma_path, rows, cols = tensor_paths['post_norm']
    audit.need(rows == 1 and cols == 1024, 'actual post-norm tensor shape')
    audit.need(sha(gamma_path) == inputs[POST_GAMMA]['f32le_sha256'], 'actual checkpoint gamma F32 SHA')
    gamma_real = f32(gamma_path)
    audit.need(len(gamma_real) == 1024, 'gamma scalar count')
    gamma_bf_path = gamma_path.with_suffix('.bf16le')
    bf = array.array('H'); bf.frombytes(gamma_bf_path.read_bytes())
    fp = array.array('I'); fp.frombytes(gamma_path.read_bytes())
    audit.need(len(bf) == len(fp) == 1024, 'paired BF16/F32 gamma length')
    audit.need(all((int(a) << 16) == int(b) for a, b in zip(bf, fp)), 'actual gamma BF16 bit expansion')
    report['actual_post_gamma'] = {'f32_sha256': sha(gamma_path), 'bf16_sha256': sha(gamma_bf_path),
                                   'BF16_to_F32_all_1024_bit_pairs_equal': True}
    real_weights = {}
    for matrix, label in [('gate', 'gate_proj'), ('up', 'up_proj'), ('down', 'down_proj')]:
        path, n, K = tensor_paths[label]
        audit.need((n, K) == ((1024, 3072) if matrix == 'down' else (3072, 1024)), 'actual matrix shape: ' + matrix)
        audit.need(path.stat().st_size == n * K * 4, 'actual matrix length: ' + matrix)
        audit.need(sha(path) == inputs[MATRIX_NAMES[matrix]]['f32le_sha256'], 'actual checkpoint matrix SHA: ' + matrix)
        real_weights[matrix] = f32(path)
    report['actual_weight_F32_SHA'] = {m: inputs[name]['f32le_sha256'] for m, name in MATRIX_NAMES.items()}
    profiles = index['profiles']
    summaries = {p['id']: p for p in summary['profiles']}
    audit.need('current_Fin10_WFin7' in profiles, 'baseline exported')
    audit.need(summary['selected_candidate'] in profiles, 'cal-selected candidate exported')
    expected_profiles = {'current_Fin10_WFin7', summary['selected_candidate']}
    audit.need(set(profiles) == expected_profiles, 'exported profile set baseline plus selected only')
    cal_selected = min(summary['profiles'], key=lambda p: p['metrics']['cal']['output']['relative_L2'])['id']
    audit.need(cal_selected == summary['selected_candidate'], 'cal-only selected profile metric minimum')
    weights_cache = {}; gamma_cache = {}; profile_checks = {}
    for profile_id, p in profiles.items():
        for field, summary_field in [('X_Fin', 'X_Fin'), ('norm_gamma_Fin', 'norm_gamma_Fin'),
                                     ('weights_Fin', 'weight_Fin'),
                                     ('M_READ_right_shift', 'M_READ_right_shift'),
                                     ('M_factor', 'M_factor'), ('M_left_shift', 'M_left_shift'),
                                     ('epsilon_code', 'epsilon_code')]:
            audit.need(p[field] == summaries[profile_id][summary_field], 'export/summary static numeric binding: ' + field)
        audit.need(p['gate_up_mid_Fin'] == 10, 'fixed native G units')
        xf = p['X_Fin']; nf = p['norm_gamma_Fin']; wfrac = p['weights_Fin']
        shifts = [nf + wfrac[0] - 10, nf + wfrac[1] - 10, 10 + wfrac[2] - xf]
        audit.need(shifts == p['M_READ_right_shift'] and all(0 <= s <= 63 for s in shifts), 'native M shifts and complete units')
        audit.need(1 <= p['epsilon_code'] <= 0xffffffff, 'native epsilon field')
        audit.need(p['M_factor'] == 1 and p['M_left_shift'] == 0, 'supported sampled M scale')
        gamma, gclips = quant16(gamma_real, nf)
        gamma_cache[profile_id] = gamma
        audit.need(gclips == summaries[profile_id]['parameter_clips']['gamma'], 'independent gamma quantization clip count')
        raw_weights = {}; signed_weights = {}; param_counts = {}
        audit.need(len(p['source_weights']) == 3, 'three source S8 matrices')
        for matrix_no, matrix in enumerate(['gate', 'up', 'down']):
            source = p['source_weights'][matrix_no]
            path = inside(numeric, source['file'])
            artifact(path)
            raw = path.read_bytes()
            audit.need(len(raw) == source['bytes'] == 3145728, 'source S8 matrix byte count')
            audit.need(sha(path) == source['sha256'], 'source S8 matrix SHA')
            codes = array.array('b'); codes.frombytes(raw)
            # Full parameter quantization is independently checked, not sampled.
            count_clip = 0; zeroed = 0; scale = float(1 << wfrac[matrix_no])
            for value, code in zip(real_weights[matrix], codes):
                if not math.isfinite(value):
                    raise ValueError('nonfinite checkpoint matrix')
                rounded = round(float(value) * scale)
                narrowed = max(-128, min(127, rounded))
                if narrowed != code:
                    raise AssertionError('full actual matrix->S8 quantization mismatch: ' + profile_id + '/' + matrix)
                count_clip += narrowed != rounded
                zeroed += value != 0 and code == 0
            audit.need(len(real_weights[matrix]) == len(codes), 'full weight quantization element count')
            audit.need(count_clip == summaries[profile_id]['parameter_clips'][matrix + '_weights'], 'weight parameter clip count')
            raw_weights[matrix] = raw; signed_weights[matrix] = codes
            param_counts[matrix] = {'all_elements_checked': len(codes), 'clipped': count_clip,
                                    'nonzero_original_quantized_to_zero': zeroed}
        weights_cache[profile_id] = signed_weights
        stream = inside(numeric, p['weights_stream_file'])
        artifact(stream)
        stream_check = canonical_stream(raw_weights, p, stream, audit)
        profile_checks[profile_id] = {'full_S8_parameter_quantization': param_counts,
                                      'canonical_weight_stream': stream_check,
                                      'actual_checkpoint_gamma_quant_clips': gclips}
    report['profiles'] = profile_checks
    case_map = {c['id']: c for c in receipt['cases']}
    audit.need(len(case_map) == 4 and sum(c['split'] == 'cal' for c in case_map.values()) == 2
               and sum(c['split'] == 'eval' for c in case_map.values()) == 2, 'four prefixes with independent cal/eval split')
    audit.need(all(len(c['token_ids']) == 4 for c in case_map.values()), 'four real tokens per prefix')
    audit.need(len(index['fixtures']) == len(profiles) * len(case_map), 'complete baseline/selected fixture coverage')
    seen = set(); results = []; dot_count = 0; dot_products = 0
    for fixture in index['fixtures']:
        profile_id = fixture['profile']; p = profiles[profile_id]; case = case_map[fixture['case']]
        audit.need((profile_id, fixture['case']) not in seen, 'duplicate fixture case/profile')
        seen.add((profile_id, fixture['case']))
        audit.need(fixture['split'] == case['split'] and fixture['position'] == len(case['token_ids']) - 1, 'actual last-token fixture identity')
        binding = {'H': 1024, 'I': 3072, 'N_EPSILON': p['epsilon_code'],
                   'M_GATE_SHIFT': p['M_READ_right_shift'][0], 'M_UP_SHIFT': p['M_READ_right_shift'][1],
                   'M_DOWN_SHIFT': p['M_READ_right_shift'][2], 'G_Fin': 10}
        audit.need(fixture['static_profile_binding'] == binding, 'compile-time profile binding')
        values = {}
        for stage, words in [('input', 128), ('norm', 128), ('gate', 384), ('up', 384),
                             ('mid', 384), ('down', 128), ('output', 128)]:
            meta = fixture['stages'][stage]; path = inside(numeric, meta['hex_file'])
            artifact(path)
            audit.need(meta['words128'] == words and sha(path) == meta['sha256'], 'stagehex SHA: ' + stage)
            values[stage] = read_hex(path, words, audit)
        fixture_dir = inside(numeric, fixture['stages']['input']['hex_file']).parent
        gamma_path = inside(numeric, fixture['gamma_hex_file']); artifact(gamma_path)
        audit.need(sha(gamma_path) == fixture['gamma_hex_sha256'], 'gamma hex SHA')
        gamma = read_hex(gamma_path, 128, audit)
        audit.need(gamma == gamma_cache[profile_id], 'all1024 actual BF16 gamma quantization')
        audit.need((fixture_dir / 'gamma.hex').read_bytes() == gamma_path.read_bytes(), 'fixture gamma alias')
        audit.need((fixture_dir / 'expected-output.hex').read_bytes() == inside(numeric, fixture['stages']['output']['hex_file']).read_bytes(), 'expected output alias')
        flag = (fixture_dir / fixture['expected_saturated_hex_file']).read_text(encoding='ascii').strip()
        audit.need(flag in ('0', '1') and bool(int(flag)) == fixture['expected_native_done_saturated'], 'golden expected saturation metadata')
        input_path = numeric / (case['id'] + '.F_input.f32le'); artifact(input_path)
        all_input = f32(input_path)
        audit.need(len(all_input) == len(case['token_ids']) * 1024, 'actual complete FP32 F-cut tensor shape')
        pos = fixture['position']; source_input = all_input[pos * 1024:(pos + 1) * 1024]
        qinput, input_clips = quant16(source_input, p['X_Fin'])
        audit.need(qinput == values['input'], 'all1024 actual FP32 F-cut input quantization')
        audit.need(input_clips == fixture['offline_input_quant_clips'], 'offline input quantization clipping')
        square = sum(x * x for x in qinput)
        rad = ((square << 16) // 1024) + (p['epsilon_code'] << 16)
        root = math.isqrt(rad)
        audit.need(root > 0, 'nonzero native N root')
        factor = (1 << 38) // root
        audit.need(factor <= 0xffffffff, 'native N factor32 range')
        norm_raw = [round(Fraction(x * g * factor, 1 << 30)) for x, g in zip(qinput, gamma)]
        norm = [clip16(x) for x in norm_raw]
        audit.need(norm == values['norm'], 'all1024 independent RMS outputs')
        norm_clips = sum(a != b for a, b in zip(norm_raw, norm))
        mid = []; gclip = False
        for group in range(384):
            begin = group * 8
            result = gref.g_vector(0, True, values['gate'][begin:begin + 8], values['up'][begin:begin + 8], 8)
            audit.need(not result['error'], 'independent G fn0 contract')
            mid.extend(result['output']); gclip |= result['saturated']
        audit.need(mid == values['mid'], 'all3072 independent mathematical G outputs')
        added = [a + b for a, b in zip(values['down'], qinput)]
        final = [clip16(x) for x in added]
        audit.need(final == values['output'], 'all1024 independent exact E residual')
        e_clips = sum(a != b for a, b in zip(added, final))
        sampled = []; sampled_m_clip = False
        for matrix_no, matrix in enumerate(['gate', 'up', 'down']):
            x = mid if matrix == 'down' else norm
            K = 3072 if matrix == 'down' else 1024
            shift = p['M_READ_right_shift'][matrix_no]
            w = weights_cache[profile_id][matrix]
            for n in SAMPLES[matrix]:
                offset = n * K
                raw = sum(int(value) * int(w[offset + k]) for k, value in enumerate(x))
                rounded = round(Fraction(raw, 1 << shift)); narrowed = clip16(rounded)
                audit.need(narrowed == values[matrix][n], 'ungrouped full-K selected M dot: ' + matrix + '/' + str(n))
                sampled_m_clip |= rounded != narrowed
                sampled.append({'matrix': matrix, 'n': n, 'K': K, 'raw_signed64': raw,
                                'READ_right_shift': shift, 'RNE': rounded, 'clipped': narrowed,
                                'matches_stage': True})
                dot_count += 1; dot_products += K
        independently_seen_sat = bool(norm_clips or gclip or e_clips or sampled_m_clip)
        if independently_seen_sat:
            audit.need(fixture['expected_native_done_saturated'], 'observed independent native saturation must be reported')
        results.append({'id': fixture['id'], 'profile': profile_id, 'split': fixture['split'],
                        'position': pos, 'actual_input_clip_count': input_clips,
                        'N_full_elements': 1024, 'N_radicand': rad, 'N_isqrt': root, 'N_factor': factor,
                        'N_clip_count': norm_clips, 'G_full_elements': 3072, 'G_any_clip': gclip,
                        'E_full_elements': 1024, 'E_clip_count': e_clips,
                        'sampled_M_full_dot_count': len(sampled), 'M_selected_full_dots': sampled,
                        'independently_observed_native_saturation': independently_seen_sat,
                        'complete_M_saturation_flag_independently_proven': False})
    audit.need(len(seen) == len(case_map) * len(profiles), 'all case/profile rows checked')
    audit.need(dot_count == 24 * len(results), '24 full-K M dots per fixture')
    report.update({'status': 'PASS_INDEPENDENT_QNUM_EXPECTATIONS_SELECTED_M_FULL_N_G_E',
                   'checks': audit.checks, 'fixtures_checked': len(results), 'fixture_results': results,
                   'full_S8_parameter_values_checked': len(profiles) * 9437184,
                   'N_elements_checked': len(results) * 1024, 'G_elements_checked': len(results) * 3072,
                   'E_elements_checked': len(results) * 1024, 'selected_M_full_dot_count': dot_count,
                   'selected_M_integer_products': dot_products,
                   'M_full_raw_or_all_saturation_proven': False,
                   'actual_accepted_RTL_dump_checked': False,
                   'quality_acceptance': False,
                   'limits': ['N/G/E complete dimensions; M only24 selected output rows per fixture',
                              'G inputs and E down input are golden stages; unselected M raw accumulators remain unproven here',
                              'no DUT output or C++ raw accumulator used',
                              'actual FP32 F-cut source is the independent C++ implementation,not official-framework equivalence',
                              'no trained/full-model quality or physical qualification']})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--numeric-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError('immutable checker output already exists: ' + str(output))
    report = {'status': 'RUNNING_INDEPENDENT_NUMERICAL_CHECK_NOT_RTL',
              'checker_sha256': sha(Path(__file__)), 'only_stdlib': True,
              'dependencies_required': REFERENCE_DEPENDENCIES}
    failed = None
    try:
        perform(args, report)
    except Exception as error:
        report['status'] = 'FAIL_INDEPENDENT_QNUM_EXPECTATIONS'
        report['error'] = str(error)
        failed = error
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8', newline='\n') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write('\n')
    if failed is not None:
        raise failed
    print('PASS_QNUM_INDEPENDENT_EXPECTATIONS fixtures=' + str(report['fixtures_checked'])
          + ' sampled_M_full_dots=' + str(report['selected_M_full_dot_count'])
          + ' full_N_G_E=true')


if __name__ == '__main__':
    main()
