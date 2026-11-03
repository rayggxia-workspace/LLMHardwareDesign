"""Independent fixed-baseline/W8 integer export audit. No C++ or RTL launch.

Checks all source S8 quantization/packing, complete N/G/E exported rows and
192 ungrouped full-K M dots. It does not accept model quality, prove all M
accumulators, or use an RTL output as a golden. Python 3.7+, stdlib only.
"""
import argparse
import array
import hashlib
import json
import math
import sys
import types
from fractions import Fraction
from pathlib import Path

REVISION = 'c1899de289a04d12100db370d81485cdf75e47ca'
PROFILES = {'current_Fin10_WFin7': 7, 'matrix_safe_x10_n10': 8}
CASES = {
    'cal_text_0': ('cal', [9707, 1879, 0, 198]),
    'cal_math_0': ('cal', [16, 10, 16, 28]),
    'eval_text_0': ('eval', [785, 8251, 374, 2613]),
    'eval_math_0': ('eval', [17, 9, 18, 28]),
}
STAGES = {'input': 1024, 'norm': 1024, 'gate': 3072, 'up': 3072,
          'mid': 3072, 'down': 1024, 'output': 1024}
FP_STAGES = {'Y': 1024, 'norm': 1024, 'gate': 3072, 'up': 3072,
             'mid': 3072, 'down': 1024, 'Z': 1024}
DEPENDENCIES = [
    'work/Melodydt/151/qnum/check_qnum_expectations.py',
    'work/Melodydt/151/f16_integer_reference.py',
    'project/rtl/block_v2/block_v2_g_tables.svh',
    'work/Melodydt/151/qnum/qwen_layer0_numeric.cpp',
    'work/Melodydt/151/qnum/run_qwen_layer0.py',
    'work/Melodydt/151/quality/quality_numeric.cpp',
    'work/Melodydt/151/quality/check_quality_expectations.py',
]
TENSORS = {
    'gamma': ('post_norm', 'model.layers.0.post_attention_layernorm.weight', [1024]),
    'gate': ('gate_proj', 'model.layers.0.mlp.gate_proj.weight', [3072, 1024]),
    'up': ('up_proj', 'model.layers.0.mlp.up_proj.weight', [3072, 1024]),
    'down': ('down_proj', 'model.layers.0.mlp.down_proj.weight', [1024, 3072]),
}


def sha(path):
    value = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1048576), b''):
            value.update(block)
    return value.hexdigest()


def read_module(path, name):
    module = types.ModuleType(name)
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
    return module


def sqrt_floor(value):
    if value < 0:
        raise ValueError('negative integer radicand')
    if not value:
        return 0
    x = 1 << ((value.bit_length() + 1) // 2)
    while True:
        y = (x + value // x) // 2
        if y >= x:
            return x
        x = y


def perform(args, report):
    repo, data, numeric = args.root.resolve(), args.data_dir.resolve(), args.numeric_dir.resolve()
    source_hashes = {name: sha(repo / name) for name in DEPENDENCIES}
    helper = read_module(repo / DEPENDENCIES[0], 'quality_frozen_math_helpers')
    audit = helper.Audit()
    audit.need(sys.byteorder == 'little', 'little-endian binary ABI')
    audit.need(round(Fraction(-3, 2)) == -2 and round(Fraction(-5, 2)) == -2,
               'independent signed ties-to-even literals')
    audit.need([sqrt_floor(n) for n in [0, 1, 2, 8, 9, 15, 16]] == [0, 1, 1, 2, 3, 3, 4],
               'independent integer sqrt literals')
    inside = helper.inside
    manifest_path = data / 'manifest.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    audit.need(manifest['status'] == 'COMPLETE_SELECTED_TENSORS_AND_ROWS', 'complete selected dataset')
    audit.need(manifest['repo'] == 'Qwen/Qwen3-0.6B' and manifest['revision'] == REVISION,
               'pinned official checkpoint repository/revision')
    case_path = inside(data, manifest['token_sequences_file'])
    case_data = json.loads(case_path.read_text(encoding='utf-8'))['token_sequences']
    observed_cases = {}
    for case in case_data:
        audit.need(case['id'] not in observed_cases, 'unique source prefix ID')
        observed_cases[case['id']] = (case['split'], case['token_ids'])
    audit.need(observed_cases == CASES, 'exact four old diagnostic prefixes, not a new holdout')
    expected_tsv = {name: (kind, ','.join(map(str, ids))) for name, (kind, ids) in CASES.items()}
    actual_tsv = {}
    for line in (numeric / 'cases.tsv').read_text(encoding='utf-8').splitlines():
        fields = line.split('\t')
        audit.need(len(fields) == 3 and fields[0] not in actual_tsv, 'unique cases TSV record')
        actual_tsv[fields[0]] = (fields[1], fields[2])
    audit.need(actual_tsv == expected_tsv, 'numeric cases match source token IDs and labels')
    table = {}
    for line in (numeric / 'tensor-map.tsv').read_text(encoding='utf-8').splitlines():
        fields = line.split('\t')
        audit.need(len(fields) == 4 and fields[0] not in table, 'unique tensor TSV entry')
        table[fields[0]] = (Path(fields[1]).resolve(), int(fields[2]), int(fields[3]))
    entries = {entry['name']: entry for entry in manifest['tensors']}
    audit.need(len(entries) == len(manifest['tensors']) == 11, 'eleven unique layer0 source tensors')
    real = {}
    input_files = {}
    for role, (label, name, shape) in TENSORS.items():
        entry = entries[name]
        audit.need(entry['shape'] == shape and entry['source_dtype'] == 'BF16', 'source shape/dtype ' + role)
        fp = inside(data, entry['f32le_file'])
        bf = inside(data, entry['bf16le_file'])
        count = 1
        for dim in shape:
            count *= dim
        audit.need(fp.stat().st_size == entry['f32le_bytes'] == count * 4, 'F32 byte count ' + role)
        audit.need(bf.stat().st_size == entry['bf16le_bytes'] == count * 2, 'BF16 byte count ' + role)
        audit.need(sha(fp) == entry['f32le_sha256'] and sha(bf) == entry['bf16le_sha256'], 'source SHA ' + role)
        words16, words32 = array.array('H'), array.array('I')
        words16.frombytes(bf.read_bytes()); words32.frombytes(fp.read_bytes())
        audit.need(all((int(x) << 16) == int(y) for x, y in zip(words16, words32)),
                   'all actual BF16/F32 scalar bit pairs ' + role)
        rows, cols = (1, shape[0]) if len(shape) == 1 else tuple(shape)
        audit.need(table[label] == (fp, rows, cols), 'numeric tensor map actual source ' + role)
        real[role] = helper.f32(fp)
        audit.need(all(math.isfinite(v) for v in real[role]), 'finite actual source ' + role)
        if role != 'gamma':
            maximum = max(abs(float(v)) for v in real[role])
            audit.need(maximum * 256 <= 127 and maximum * 512 > 127,
                       'independent symmetric no-clamp safe WFin exactly8 ' + role)
        input_files[role] = {'f32le_sha256': sha(fp), 'bf16le_sha256': sha(bf), 'values': count}
    gref, g_validation = helper.load_g_reference(repo, audit)
    summary_path = numeric / 'numeric-summary.json'
    index_path = numeric / 'rtl-fixture-index.json'
    summary = json.loads(summary_path.read_text(encoding='utf-8'))
    index = json.loads(index_path.read_text(encoding='utf-8'))
    audit.need(summary['status'] == 'FIXED_BASELINE_W8_LEGACY_REGRESSION_NOT_MODEL_QUALITY', 'fixed regression status')
    audit.need(summary['selection'] == 'fixed_profiles_no_selection_legacy_regression_not_holdout', 'no cal/eval selection')
    audit.need(summary['W8_safe_fraction_all_matrices_verified'] is True, 'explicit fixed W8 safety assertion')
    audit.need(summary['quality_acceptance'] is False and 'selected_candidate' not in summary,
               'no inferred quality or selected candidate')
    audit.need(summary['cal_cases'] == summary['eval_cases'] == 2, 'old split label counts')
    summaries = {p['id']: p for p in summary['profiles']}
    audit.need(len(summaries) == len(summary['profiles']) == 2 and set(summaries) == set(PROFILES),
               'exact two fixed numerical profiles')
    profiles = index['profiles']
    audit.need(set(profiles) == set(PROFILES), 'exact baseline/W8 RTL export domain')
    weights, gammas, profile_results = {}, {}, {}
    for pid, wf in PROFILES.items():
        p, s = profiles[pid], summaries[pid]
        for key, expected in {'X_Fin': 10, 'norm_gamma_Fin': 10, 'gate_up_mid_Fin': 10,
                              'M_READ_right_shift': [wf] * 3, 'M_factor': 1,
                              'M_left_shift': 0, 'epsilon_code': 1}.items():
            audit.need(p[key] == s[key] == expected, 'fixed profile binding ' + pid + '/' + key)
        audit.need(p['weights_Fin'] == s['weight_Fin'] == [wf] * 3, 'fixed S8 weight precision')
        for kind in ['cal', 'eval']:
            audit.need(set(s['metrics'][kind]) == set(STAGES), 'complete stage metric domain')
            for stage, width in STAGES.items():
                metric = s['metrics'][kind][stage]
                audit.need(metric['elements'] == 8 * width and 0 <= metric['clipped'] <= 8 * width,
                           'full old-prefix metric element/clip count')
                audit.need(metric['clip_fraction'] == metric['clipped'] / float(metric['elements']),
                           'clip fraction arithmetic')
                for key in ['RMSE', 'max_abs_error', 'relative_L2']:
                    audit.need(math.isfinite(metric[key]) and metric[key] >= 0, 'finite nonnegative metric')
        gamma, gamma_clip = helper.quant16(real['gamma'], 10)
        gammas[pid] = gamma
        audit.need(gamma_clip == s['parameter_clips']['gamma'], 'actual gamma quantization clip count')
        raw_weights, signed_weights, parameter_results = {}, {}, {}
        audit.need(len(p['source_weights']) == 3, 'three S8 matrices')
        for i, matrix in enumerate(['gate', 'up', 'down']):
            source = p['source_weights'][i]
            path = inside(numeric, source['file'])
            raw = path.read_bytes()
            audit.need(path.name == matrix + '.s8' and len(raw) == source['bytes'] == 3145728,
                       'matrix identity/complete byte length')
            audit.need(sha(path) == source['sha256'], 'S8 matrix index SHA')
            codes = array.array('b'); codes.frombytes(raw)
            audit.need(len(codes) == len(real[matrix]), 'complete parameter scalar count')
            clips, zeroed = 0, 0
            for value, code in zip(real[matrix], codes):
                rounded = round(float(value) * (1 << wf))
                narrowed = max(-128, min(127, rounded))
                if narrowed != code:
                    raise AssertionError('full F32-to-S8 mismatch ' + pid + '/' + matrix)
                clips += narrowed != rounded
                zeroed += value != 0 and code == 0
            audit.need(clips == s['parameter_clips'][matrix + '_weights'], 'complete parameter clip count')
            raw_weights[matrix], signed_weights[matrix] = raw, codes
            parameter_results[matrix] = {'all_elements_checked': len(codes), 'clipped': clips,
                                         'nonzero_original_quantized_to_zero': zeroed}
        weights[pid] = signed_weights
        stream = helper.canonical_stream(raw_weights, p, inside(numeric, p['weights_stream_file']), audit)
        profile_results[pid] = {'all_S8_parameter_quantization': parameter_results,
                                'canonical_weight_stream': stream, 'gamma_quant_clips': gamma_clip}
    fp32_artifacts = {}
    expected_fp_tsv = set()
    for case, (kind, ids) in CASES.items():
        for stage, width in FP_STAGES.items():
            relative = 'fp32/{}/{}.f32le'.format(case, stage)
            path = inside(numeric, relative)
            values = helper.f32(path)
            audit.need(len(values) == len(ids) * width and all(math.isfinite(v) for v in values),
                       'complete finite FP32 framework-comparison matrix ' + case + '/' + stage)
            fp32_artifacts[relative] = {'bytes': path.stat().st_size, 'sha256': sha(path)}
            expected_fp_tsv.add((case, kind, stage, str(len(ids)), str(width), relative))
        for stage, alias in [('Y', '.F_input.f32le'), ('Z', '.layer0_FP32_output.f32le')]:
            audit.need((numeric / (case + alias)).read_bytes() ==
                       (numeric / 'fp32' / case / (stage + '.f32le')).read_bytes(), 'legacy FP32 alias')
    fp_lines = [tuple(line.split('\t')) for line in (numeric / 'fp32-stage-index.tsv').read_text(encoding='utf-8').splitlines()]
    audit.need(len(fp_lines) == len(set(fp_lines)) == 28 and set(fp_lines) == expected_fp_tsv,
               'exact 28 full FP32 matrices in stage index')
    audit.need(len(index['fixtures']) == 8, 'eight fixed last-token fixture records')
    seen, results, dot_count, products = set(), [], 0, 0
    for fixture in index['fixtures']:
        pid, case = fixture['profile'], fixture['case']
        audit.need(pid in PROFILES and case in CASES and (pid, case) not in seen, 'unique legal fixture identity')
        seen.add((pid, case)); wf = PROFILES[pid]
        audit.need(fixture['id'] == case + '_pos3' and fixture['position'] == 3
                   and fixture['split'] == CASES[case][0], 'fixed old-prefix final-token identity')
        audit.need(fixture['static_profile_binding'] == {'H': 1024, 'I': 3072, 'N_EPSILON': 1,
                   'M_GATE_SHIFT': wf, 'M_UP_SHIFT': wf, 'M_DOWN_SHIFT': wf, 'G_Fin': 10},
                   'explicit static compile binding')
        values = {}
        for stage, width in STAGES.items():
            meta = fixture['stages'][stage]
            path = inside(numeric, meta['hex_file'])
            audit.need(meta['words128'] == width // 8 and sha(path) == meta['sha256'], 'stage hex index SHA/count')
            values[stage] = helper.read_hex(path, width // 8, audit)
            raw = array.array('h', values[stage]).tobytes()
            audit.need(path.with_suffix('.s16le').read_bytes() == raw, 'complete stage hex/binary equality')
        fd = inside(numeric, fixture['stages']['input']['hex_file']).parent
        gamma_path = inside(numeric, fixture['gamma_hex_file'])
        audit.need(sha(gamma_path) == fixture['gamma_hex_sha256'], 'gamma index SHA')
        gamma = helper.read_hex(gamma_path, 128, audit)
        audit.need(gamma == gammas[pid] and (fd / 'gamma.hex').read_bytes() == gamma_path.read_bytes(), 'full gamma and alias')
        audit.need((fd / 'expected-output.hex').read_bytes() == (fd / 'output.hex').read_bytes(), 'expected output alias')
        flag = (fd / fixture['expected_saturated_hex_file']).read_text(encoding='ascii').strip()
        audit.need(flag in ('0', '1') and bool(int(flag)) == fixture['expected_native_done_saturated'], 'saturation alias and metadata')
        source_y = helper.f32(numeric / 'fp32' / case / 'Y.f32le')[3072:4096]
        qinput, input_clips = helper.quant16(source_y, 10)
        audit.need(qinput == values['input'] and input_clips == fixture['offline_input_quant_clips'], 'all1024 F-cut quantization')
        rad = ((sum(x * x for x in qinput) << 16) // 1024) + (1 << 16)
        root = sqrt_floor(rad); audit.need(root > 0, 'N nonzero root')
        factor = (1 << 38) // root; audit.need(factor <= 0xffffffff, 'N factor32')
        raw_norm = [round(Fraction(x * g * factor, 1 << 30)) for x, g in zip(qinput, gamma)]
        norm = [helper.clip16(x) for x in raw_norm]
        audit.need(norm == values['norm'], 'all1024 independent N output')
        nclips = sum(a != b for a, b in zip(raw_norm, norm))
        raw_mid = [round(Fraction(gref.g_activation(0, a) * b, 1 << 10))
                   for a, b in zip(values['gate'], values['up'])]
        mid = [helper.clip16(x) for x in raw_mid]
        audit.need(mid == values['mid'], 'all3072 mathematical G outputs')
        gclips = sum(a != b for a, b in zip(raw_mid, mid))
        raw_final = [a + b for a, b in zip(values['down'], qinput)]
        final = [helper.clip16(x) for x in raw_final]
        audit.need(final == values['output'], 'all1024 exact E residual outputs')
        eclips = sum(a != b for a, b in zip(raw_final, final))
        sampled, mclip = [], False
        for matrix in ['gate', 'up', 'down']:
            x = mid if matrix == 'down' else norm
            K = 3072 if matrix == 'down' else 1024
            w = weights[pid][matrix]
            for n in helper.SAMPLES[matrix]:
                raw = sum(int(v) * int(w[n * K + k]) for k, v in enumerate(x))
                rounded = round(Fraction(raw, 1 << wf)); code = helper.clip16(rounded)
                audit.need(code == values[matrix][n], 'independent full-K M sample ' + matrix + '/' + str(n))
                mclip |= code != rounded
                sampled.append({'matrix': matrix, 'n': n, 'K': K, 'raw_signed64': raw,
                                'READ_right_shift': wf, 'RNE': rounded, 'clipped': code})
                dot_count += 1; products += K
        observed_sat = bool(nclips or gclips or eclips or mclip)
        if observed_sat:
            audit.need(fixture['expected_native_done_saturated'], 'independently observed native clipping reported')
        results.append({'id': fixture['id'], 'profile': pid, 'N_elements': 1024, 'N_clip_count': nclips,
                        'G_elements': 3072, 'G_clip_count': gclips, 'E_elements': 1024, 'E_clip_count': eclips,
                        'N_radicand': rad, 'N_factor': factor, 'input_quant_clips': input_clips,
                        'M_fullK_samples': sampled, 'observed_native_saturation': observed_sat,
                        'complete_M_saturation_flag_independently_proven': False})
    audit.need(seen == {(p, c) for p in PROFILES for c in CASES}, 'complete profile/case Cartesian product')
    audit.need(dot_count == 192, '192 independent full-K M sampled outputs')
    audit.need(all(sha(repo / name) == value for name, value in source_hashes.items()), 'reference/source hashes unchanged')
    report.update({'status': 'PASS_QUALITY_EXPECTATIONS_FIXED_PROFILES_SAMPLED_M_FULL_N_G_E',
                   'checks': audit.checks, 'revision': REVISION, 'manifest_sha256': sha(manifest_path),
                   'case_source_sha256': sha(case_path), 'summary_sha256': sha(summary_path),
                   'fixture_index_sha256': sha(index_path), 'dependencies_sha256': source_hashes,
                   'actual_F_tensor_sources': input_files, 'G_table_validation': g_validation,
                   'profiles': profile_results, 'fixtures_checked': 8, 'fixture_results': results,
                   'FP32_framework_comparison_inputs': fp32_artifacts,
                   'full_S8_parameter_values_checked': 18874368, 'N_elements_checked': 8192,
                   'G_elements_checked': 24576, 'E_elements_checked': 8192,
                   'selected_M_full_dot_count': dot_count, 'selected_M_integer_products': products,
                   'M_full_raw_or_all_saturation_proven': False, 'actual_RTL_dump_checked': False,
                   'framework_equivalence_proven': False, 'quality_acceptance': False,
                   'limits': ['old diagnostic prefixes are regression, not a new held-out quality corpus',
                              'N/G/E complete eight exported rows; M only24 full-K selected outputs per row',
                              'golden M stage inputs do not prove all unsampled M outputs or all clipping',
                              'independent FP32 creates F input; complete integer Attention not evaluated',
                              'framework comparison, product quality, permanent binding and physical gates separate']})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--data-dir', type=Path, required=True)
    parser.add_argument('--numeric-dir', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError('immutable check result exists: ' + str(output))
    report = {'status': 'RUNNING_QUALITY_EXPECTATIONS_NOT_RTL', 'checker_sha256': sha(Path(__file__)),
              'quality_acceptance': False, 'only_stdlib': True}
    error = None
    try:
        perform(args, report)
    except Exception as caught:
        error = caught
        report.update(status='FAIL_QUALITY_EXPECTATIONS', error=str(caught))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    if error is not None:
        raise error
    print('PASS_QUALITY_EXPECTATIONS fixtures=8 sampled_M_full_dots=192 full_N_G_E=true')


if __name__ == '__main__':
    main()
