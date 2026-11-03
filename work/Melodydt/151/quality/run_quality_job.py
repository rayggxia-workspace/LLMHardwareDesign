"""Frozen legacy-prefix FP32 reference and baseline/W8 integer RTL regression.

Server/container/Slurm only; this file neither submits jobs nor uses SSH.
All artifacts are new, owner-local and source-bound. A failed gate stops the
pipeline and preserves its receipt/logs; no product-quality verdict is issued.
"""
import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import types

OWNER = Path('/public/home/yuzelu/Melodydt')
VERILATOR = '/public/home/yuzelu/opt/eda/verilator-5.042/bin/verilator'
HELPER = 'work/Melodydt/151/quality'
SELECTION = 'fixed_profiles_no_selection_legacy_regression_not_holdout'


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def need(condition, message):
    if not condition:
        raise ValueError(message)


def fingerprint(path):
    h, size = hashlib.sha256(), 0
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1048576), b''):
            h.update(block)
            size += len(block)
    return {'bytes': size, 'sha256': h.hexdigest()}


def owner_path(path):
    path = Path(path).resolve()
    need(OWNER in path.parents, 'path must be inside owner directory: ' + str(path))
    need(not any(c in str(path) for c in '\t\r\n'), 'control byte in path')
    return path


def inside(root, relative):
    need(isinstance(relative, str) and not Path(relative).is_absolute(), 'relative path required')
    path = (root / relative).resolve()
    need(root in path.parents, 'path escapes bound directory: ' + relative)
    return path


def read_json(path):
    def nonfinite(value):
        raise ValueError('nonfinite JSON value: ' + value)
    return json.loads(path.read_text(encoding='utf-8'), parse_constant=nonfinite)


def write_json(path, value):
    path.write_bytes((json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8'))


def load_helper(path):
    module = types.ModuleType('quality_frozen_qnum_bridge')
    module.__file__ = str(path)
    exec(compile(path.read_bytes(), str(path), 'exec'), module.__dict__)
    return module


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--root', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--dataset', type=Path, required=True)
    ap.add_argument('--source-commit', required=True)
    ap.add_argument('--container-sha256', required=True)
    ap.add_argument('--python-deps', type=Path, required=True)
    args = ap.parse_args()
    root, out, dataset, deps = [owner_path(p) for p in
                                (args.root, args.output, args.dataset, args.python_deps)]
    need(not out.exists(), 'output is immutable; choose a new run directory')
    need(all(p.is_dir() for p in (root, dataset, deps)), 'source/data/Python dependencies must exist')
    need(not any(p == out or p in out.parents or out in p.parents for p in (root, dataset, deps)),
         'output must be separate from all immutable inputs')
    need(bool(re.fullmatch('[0-9a-f]{40}', args.source_commit)), 'actual40hex source commit required')
    need(sys.byteorder == 'little', 'little-endian BF16/F32 verification required')
    need(os.environ.get('SLURM_JOB_ID', '').isdigit(), 'Slurm allocation required')
    need(os.environ.get('SLURM_JOB_NAME') == 'zenanyan-quality', 'wrong Slurm job name')
    need(int(os.environ.get('SLURM_CPUS_PER_TASK', '0')) >= 8, 'at least8 assigned CPUs required')
    image_env = os.environ.get('APPTAINER_CONTAINER') or os.environ.get('SINGULARITY_CONTAINER')
    need(bool(image_env), 'must run inside the frozen Apptainer/Singularity container')
    image = owner_path(image_env)
    need(image.is_file(), 'container image must be visible for SHA verification')
    out.mkdir(parents=True)
    for name in ('logs', 'results', 'build'):
        (out / name).mkdir()
    receipt_path = out / 'results/run-receipt.json'
    receipt = {'schema_version': 1, 'status': 'RUNNING_QUALITY_REGRESSION',
               'started_utc': now(), 'source_commit': args.source_commit,
               'node': platform.node(), 'python': sys.version, 'root': str(root),
               'output': str(out), 'dataset': str(dataset), 'python_deps': str(deps),
               'container': str(image), 'container_sha256': args.container_sha256,
               'slurm': {k: os.environ.get(k) for k in
                         ('SLURM_JOB_ID', 'SLURM_JOB_NAME', 'SLURM_CPUS_PER_TASK',
                          'SLURM_JOB_PARTITION', 'SLURM_JOB_NODELIST')},
               'commands': [], 'inputs': [], 'data_inputs': [], 'fixture_checks': [],
               'generated_before_RTL': [], 'warnings': {},
               'dataset_role': 'previously observed four fixed prefixes; regression, not unseen holdout',
               'profile_selection': 'fixed before run; no calibration/evaluation selection',
               'product_quality_accepted': False, 'integer_A_to_F_quality_accepted': False,
               'full_model_inference': False, 'physical_qualified': False}
    environment = os.environ.copy()
    environment.update(PYTHONPATH=str(deps), PYTHONDONTWRITEBYTECODE='1',
                       HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                       TOKENIZERS_PARALLELISM='false', OMP_DYNAMIC='FALSE')
    for key in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS',
                'BLIS_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        environment[key] = '8'
    receipt['bounded_environment'] = {k: environment[k] for k in
        ('PYTHONPATH', 'PYTHONDONTWRITEBYTECODE', 'HF_HUB_OFFLINE', 'TRANSFORMERS_OFFLINE',
         'TOKENIZERS_PARALLELISM', 'OMP_NUM_THREADS', 'MKL_NUM_THREADS',
         'OPENBLAS_NUM_THREADS', 'OMP_DYNAMIC')}

    def save():
        write_json(receipt_path, receipt)

    def run(label, argv):
        log = out / 'logs' / (label + '.log')
        need(not log.exists(), 'duplicate command label: ' + label)
        entry = {'label': label, 'argv': [str(x) for x in argv], 'exit_code': None,
                 'status': 'RUNNING', 'started_utc': now(), 'log': str(log.relative_to(out))}
        receipt['commands'].append(entry)
        receipt['current_phase'] = label
        save()
        try:
            with log.open('xb') as stream:
                result = subprocess.run(argv, cwd=str(root), env=environment,
                                        stdout=stream, stderr=subprocess.STDOUT)
            entry.update(exit_code=result.returncode,
                         status='PASS' if result.returncode == 0 else 'FAIL')
        except Exception as error:
            entry.update(status='LAUNCH_FAIL', launch_error=repr(error))
            raise
        finally:
            entry['ended_utc'] = now()
            if log.exists():
                entry.update(fingerprint(log))
            save()
        need(entry['exit_code'] == 0, label + ' failed with exit ' + str(entry['exit_code']))
        return log.read_text(encoding='utf-8', errors='replace')

    locked_data = {}

    def lock_data(path, expected=None, label=None):
        path = owner_path(path)
        actual = fingerprint(path)
        if expected is not None:
            need(all(actual[k] == v for k, v in expected.items()), 'input mismatch: ' + str(path))
        if str(path) not in locked_data:
            locked_data[str(path)] = actual
            receipt['data_inputs'].append({'path': str(path), 'label': label, **actual})
        else:
            need(actual == locked_data[str(path)], 'input changed during use: ' + str(path))
        return actual

    def inventory(directory):
        return [{'path': str(p.relative_to(out)), **fingerprint(p)}
                for p in sorted(directory.rglob('*')) if p.is_file()]

    save()
    try:
        contract_path = root / HELPER / 'quality-contract.json'
        contract = read_json(contract_path)
        need(contract['container_sha256'] == args.container_sha256, 'container binding mismatch')
        image_fp = fingerprint(image)
        need(image_fp['sha256'] == args.container_sha256, 'actual container SHA mismatch')
        receipt['container_verified'] = image_fp
        need(Path(__file__).resolve() == inside(root, contract['runner_script']), 'executed runner not source-bound')
        manifest_path = root / 'source-manifest.json'
        manifest = read_json(manifest_path)
        need(manifest['source_commit'] == args.source_commit, 'source commit mismatch')
        required = set(contract['compile_sources'] + contract['source_includes'] +
                       contract['reference_dependencies'] + [contract[k] for k in
                       ('engine_source', 'checker_script', 'framework_script', 'runner_script',
                        'qnum_helper', 'rtl_contract')] + [HELPER + '/quality-contract.json'])
        need(len(manifest['files']) == len({row['path'] for row in manifest['files']}), 'duplicate source')
        need({row['path'] for row in manifest['files']} == required, 'source dependency closure mismatch')
        for row in manifest['files']:
            path = inside(root, row['path'])
            need(fingerprint(path) == {k: row[k] for k in ('bytes', 'sha256')}, 'source SHA: ' + row['path'])
            receipt['inputs'].append(row)
        receipt['source_manifest'] = fingerprint(manifest_path)
        rtl_contract = read_json(inside(root, contract['rtl_contract']))
        expected_cases = contract['expected_case_ids']
        need(expected_cases == rtl_contract['expected_case_ids'] and len(set(expected_cases)) == 7,
             'exact frozen seven RTL cases required')
        need(contract['compile_sources'] == rtl_contract['compile_sources'], 'inherited RTL sources changed')
        need(fingerprint(inside(root, contract['compile_sources'][-1]))['sha256'] == rtl_contract['tb_sha256'],
             'inherited qnum TB SHA changed')
        need(fingerprint(inside(root, 'project/rtl/block_connection_w4/block_w4_qnum_top.sv'))['sha256'] == rtl_contract['top_sha256'],
             'inherited qnum top SHA changed')
        helper = load_helper(inside(root, contract['qnum_helper']))

        # Validate the complete selected tensor ABI before constructing engine TSVs.
        data_manifest_path = dataset / 'manifest.json'
        lock_data(data_manifest_path, {'sha256': contract['dataset_manifest_sha256']}, 'selected model manifest')
        dm = read_json(data_manifest_path)
        need(dm['status'] == 'COMPLETE_SELECTED_TENSORS_AND_ROWS', 'partial selected dataset')
        need(dm['repo'] == contract['model_repo'] and dm['revision'] == contract['model_revision'], 'model revision')
        config_path = inside(dataset, dm['config_file'])
        cases_path = inside(dataset, dm['token_sequences_file'])
        lock_data(config_path, {'sha256': contract['dataset_config_sha256']}, 'config')
        lock_data(cases_path, {'sha256': contract['dataset_token_sequences_sha256']}, 'legacy prefixes')
        for key in ('vocab_file', 'tokenizer_config_file'):
            lock_data(inside(dataset, dm[key]), label=key)
        config = read_json(config_path)
        for key, value in {'hidden_size': 1024, 'intermediate_size': 3072,
            'num_attention_heads': 16, 'num_key_value_heads': 8, 'head_dim': 128,
            'rms_norm_eps': 1e-6, 'rope_theta': 1000000, 'attention_bias': False,
            'hidden_act': 'silu'}.items():
            need(config.get(key) == value, 'unexpected model config: ' + key)
        actual_cases = [{k: row[k] for k in ('id', 'split', 'token_ids', 'pieces')}
                        for row in read_json(cases_path)['token_sequences']]
        need(actual_cases == contract['cases'], 'legacy case identity/order changed')
        need([row['id'] for row in actual_cases] == contract['expected_prefix_ids'], 'prefix IDs')
        need(len(actual_cases) == 4 and all(len(row['token_ids']) == 4 for row in actual_cases), 'four by four prefix shape')
        entries = {row['name']: row for row in dm['tensors']}
        need(len(entries) == len(dm['tensors']) == 11, 'exact11 selected tensors required')
        tensor_lines, verified = [], 0
        for label, (name, shape) in helper.TENSORS.items():
            fp, count = helper.check_tensor(dataset, entries[name], shape)
            for suffix in ('bf16le', 'f32le'):
                lock_data(inside(dataset, entries[name][suffix + '_file']),
                    {'bytes': entries[name][suffix + '_bytes'], 'sha256': entries[name][suffix + '_sha256']}, name)
            tensor_lines.append('\t'.join([label, str(fp), str(shape[0] if len(shape) == 2 else 1), str(shape[-1])]))
            verified += count
        embeddings = {row['token_id']: row for row in dm['embedding_rows']}
        needed_tokens = sorted({token for case in actual_cases for token in case['token_ids']})
        for token in needed_tokens:
            need(type(token) is int and 0 <= token < 151936 and token in embeddings, 'missing/invalid token row')
            entry = embeddings[token]
            fp, count = helper.check_tensor(dataset, entry, [1024])
            for suffix in ('bf16le', 'f32le'):
                lock_data(inside(dataset, entry[suffix + '_file']),
                    {'bytes': entry[suffix + '_bytes'], 'sha256': entry[suffix + '_sha256']}, 'embedding/' + str(token))
            tensor_lines.append('\t'.join(['embedding_' + str(token), str(fp), '1', '1024']))
            verified += count
        receipt['BF16_to_F32_values_bit_verified'] = verified
        receipt['cases'] = actual_cases
        numeric = out / 'numeric'
        numeric.mkdir()
        (numeric / 'tensor-map.tsv').write_bytes(('\n'.join(tensor_lines) + '\n').encode('utf-8'))
        (numeric / 'cases.tsv').write_bytes(('\n'.join('\t'.join([row['id'], row['split'],
             ','.join(map(str, row['token_ids']))]) for row in actual_cases) + '\n').encode('utf-8'))
        engine = out / 'build/quality-numeric'
        run('compiler-version', ['g++', '--version'])
        run('compile-numeric', ['g++', '-std=c++17', '-O2', '-ffp-contract=off', '-fopenmp',
                              str(inside(root, contract['engine_source'])), '-o', str(engine)])
        selftest = run('numeric-selftest', [str(engine), '--self-test'])
        need(re.findall(r'^(PASS_QUALITY_NUMERIC_SELFTEST)[ \t]*$', selftest, re.M) == ['PASS_QUALITY_NUMERIC_SELFTEST'],
             'numeric self-test marker missing/duplicate')
        text = run('numeric', [str(engine), str(numeric / 'tensor-map.tsv'), str(numeric / 'cases.tsv'), str(numeric)])
        need(re.findall(r'^(PASS_QUALITY_NUMERIC profiles=2 legacy_prefixes=4 exported_fixtures=8)[ \t]*$', text, re.M) ==
             ['PASS_QUALITY_NUMERIC profiles=2 legacy_prefixes=4 exported_fixtures=8'],
             'numeric complete output marker missing')
        summary = read_json(numeric / 'numeric-summary.json')
        need(summary['selection'] == SELECTION and summary['quality_acceptance'] is False,
             'numeric profile selection/quality scope changed')
        need(summary['W8_safe_fraction_all_matrices_verified'] is True, 'fixed W8 safety not established')
        expected_profiles = {row['id']: row for row in contract['profiles']}
        summaries = {row['id']: row for row in summary['profiles']}
        need(len(summaries) == len(summary['profiles']) == 2 and set(summaries) == set(expected_profiles), 'exact fixed profiles')
        for pid, p in expected_profiles.items():
            s = summaries[pid]
            for key in ('X_Fin', 'norm_gamma_Fin', 'M_READ_right_shift'):
                need(s[key] == p[key], 'numerical binding differs: ' + pid + '/' + key)
            need(s['weight_Fin'] == p['weights_Fin'] and s['epsilon_code'] == p['N_EPSILON'], 'weight/epsilon binding')
            need(s['M_factor'] == 1 and s['M_left_shift'] == 0 and s['gate_up_mid_Fin'] == 10, 'native fixed arithmetic')
            need(all(0 <= v <= contract['integer_gates']['weight_and_gamma_quantization_clips_max']
                     for v in s['parameter_clips'].values()), 'parameter clipping exceeds frozen gate')

        # Preserve C++ canonical bytes before the independent old Python packer
        # rebuilds the same stream. No prior run or source file is rewritten.
        cpp_streams = {}
        for pid in expected_profiles:
            original = numeric / 'rtl_exports' / pid / 'weights-stream.bin'
            cpp_streams[pid] = fingerprint(original)
            copy = out / 'results' / ('cpp-canonical-' + pid + '.bin')
            shutil.copyfile(str(original), str(copy))
            need(fingerprint(copy) == cpp_streams[pid], 'C++ canonical archive copy differs')
        index = helper.index_rtl_exports(numeric)
        index['selection'] = contract['profile_selection']
        index['dataset_role'] = contract['dataset_role']
        index['status'] = 'PREPARED_FIXED_BASELINE_W8_LEGACY_REGRESSION_NOT_RTL_EXECUTED'
        index['binding_target'] = 'unchanged block_w4_qnum_top/TB with compile-time -G parameters; no new RTL'
        write_json(numeric / 'rtl-fixture-index.json', index)
        receipt['cpp_vs_python_canonical'] = []
        for pid, original in cpp_streams.items():
            rebuilt = numeric / index['profiles'][pid]['weights_stream_file']
            need(fingerprint(rebuilt) == original, 'C++/Python canonical packing differs: ' + pid)
            receipt['cpp_vs_python_canonical'].append({'profile': pid, 'passed': True, **original})
        need(len(index['fixtures']) == contract['expected_fixture_count'] == 8, 'eight exported rows required')
        expected_pairs = {(pid, case['id']) for pid in expected_profiles for case in actual_cases}
        need({(x['profile'], x['case']) for x in index['fixtures']} == expected_pairs, 'fixture Cartesian coverage')
        for fixture in index['fixtures']:
            p = expected_profiles[fixture['profile']]
            need(fixture['position'] == 3, 'only frozen final prefix token3 is admitted')
            need({k: fixture['static_profile_binding'][k] for k in p['params']} == p['params'], 'fixture static profile mismatch')
        receipt['numeric_summary'] = summary
        receipt['numeric_summary_file'] = fingerprint(numeric / 'numeric-summary.json')
        receipt['generated_before_RTL'] = inventory(numeric)
        save()

        # Fail closed before RTL on any framework/API/reference or tolerance failure.
        framework = out / 'framework'
        run('framework-compare', [sys.executable, str(inside(root, contract['framework_script'])),
             '--data-dir', str(dataset), '--cpp-dir', str(numeric), '--output-dir', str(framework),
             '--source-commit', args.source_commit, '--threads', '8'])
        fs = read_json(framework / 'framework-summary.json')
        need(fs['reference_qualification_passed'] is True and fs['comparison_count'] == 28, 'framework reference gate')
        need({(row['case'], row['stage']) for row in fs['comparisons']} ==
             {(case['id'], stage) for case in actual_cases for stage in contract['framework']['stages']}, 'framework28 stage domain')
        for row in fs['comparisons']:
            metric = row['metrics']
            need(math.isfinite(metric['max_abs_error']) and math.isfinite(metric['relative_L2']) and
                 metric['max_abs_error'] <= contract['framework']['absolute_error_max'] and
                 metric['relative_L2'] <= contract['framework']['relative_L2_max'], 'framework frozen tolerance')
            trace = inside(framework, row['official_trace'])
            need(fingerprint(trace) == {'bytes': row['official_bytes'], 'sha256': row['official_sha256']}, 'framework trace SHA')
        receipt['framework_reference'] = {'status': fs['status'], 'comparisons': fs['comparison_count'],
            'environment': fs['environment'], 'official_model_source': fs['official_model_source'],
            'summary': fingerprint(framework / 'framework-summary.json'), 'product_quality_accepted': False}
        independent_path = out / 'results/independent-expectations.json'
        run('independent-expectations', [sys.executable, str(inside(root, contract['checker_script'])),
             '--root', str(root), '--data-dir', str(dataset), '--numeric-dir', str(numeric), '--output', str(independent_path)])
        independent = read_json(independent_path)
        need(independent['status'] == 'PASS_QUALITY_EXPECTATIONS_FIXED_PROFILES_SAMPLED_M_FULL_N_G_E' and
             independent['fixtures_checked'] == 8 and independent['selected_M_full_dot_count'] >= 192,
             'independent integer golden gate')
        receipt['independent_expectations'] = {'status': independent['status'], **fingerprint(independent_path)}
        run('verilator-version', [VERILATOR, '--version'])
        executables = {}
        for pid, p in expected_profiles.items():
            obj = out / 'build' / ('obj_' + pid)
            command = [VERILATOR, '--binary', '--timing', '--assert', '--threads', '1', '-j', '8',
                '-Wno-fatal', '--top-module', contract['top'], '--Mdir', str(obj)]
            command += ['-G' + k + '=' + str(v) for k, v in p['params'].items()]
            command += ['-I' + str(inside(root, q)) for q in contract['include_dirs']]
            command += contract['compile_sources']
            build_text = run('compile-rtl-' + pid, command)
            receipt['warnings'][pid] = re.findall(r'^%Warning[^\n]*', build_text, re.M)
            executables[pid] = obj / ('V' + contract['top'])
        total_markers = 0
        for fixture in index['fixtures']:
            pid = fixture['profile']
            label = pid + '--' + fixture['case']
            weights = inside(numeric, index['profiles'][pid]['weights_stream_file'])
            need(fingerprint(weights) == {'bytes': contract['expected_accepted_bytes_per_fixture'],
                 'sha256': fixture['weights_stream_sha256']}, 'fixture canonical stream binding')
            dump = out / 'results' / ('accepted-' + label + '.bin')
            need(not dump.exists(), 'actual dump must be new')
            command = [str(executables[pid]), '+dump=' + str(dump), '+weights=' + str(weights),
                '+gamma=' + str(inside(numeric, fixture['gamma_hex_file'])),
                '+expected_sat=' + str(int(fixture['expected_native_done_saturated']))]
            for stage, record in fixture['stages'].items():
                stage_path = inside(numeric, record['hex_file'])
                need(fingerprint(stage_path)['sha256'] == record['sha256'], 'stage SHA before simulation')
                command.append('+' + stage + '=' + str(stage_path))
            text = run('simulate-' + label, command)
            observed = re.findall(r'^CASE_PASS ([A-Z][A-Z0-9_]+)\s*$', text, re.M)
            summaries_seen = re.findall(r'^' + re.escape(contract['summary_prefix']) + r' cases=(\d+)\s*$', text, re.M)
            actual = fingerprint(dump)
            passed = (observed == expected_cases and summaries_seen == ['7'] and
                not re.search(r'FAIL_|%Error|%Fatal|Assertion failed|Aborting', text) and
                actual == {'bytes': contract['expected_accepted_bytes_per_fixture'],
                           'sha256': fixture['weights_stream_sha256']})
            receipt['fixture_checks'].append({'profile': pid, 'case': fixture['case'],
                'fixture': fixture['id'], 'position': fixture['position'],
                'static_params': expected_profiles[pid]['params'], 'observed_case_ids': observed,
                'summary': summaries_seen, 'passed': passed, 'accepted_dump': str(dump), **actual})
            total_markers += len(observed)
            save()
            need(passed, 'strict seven-case/stage/accepted-stream RTL gate: ' + label)
        need(len(receipt['fixture_checks']) == 8 and total_markers == contract['expected_markers_total'] == 56,
             'eight fixtures/fifty-six markers required')
        receipt['all_56_RTL_markers_passed'] = True
        receipt['framework_reference_passed'] = True
        receipt['integer_RTL_regression_passed'] = True
        receipt['status'] = 'PASS_FIXED_LEGACY_REFERENCE_AND_BASELINE_W8_RTL_NOT_PRODUCT_QUALITY'
    except Exception as error:
        receipt['status'] = 'FAIL_QUALITY_REGRESSION'
        receipt['failure'] = {'type': type(error).__name__, 'message': str(error)}
    finally:
        # Retain all failed stages, then verify every source/data/generated input
        # that was actually used; do not silently promote a partial run to PASS.
        integrity_errors = []
        for row in receipt['inputs']:
            try:
                need(fingerprint(inside(root, row['path'])) == {k: row[k] for k in ('bytes', 'sha256')},
                     'source changed: ' + row['path'])
            except Exception as error:
                integrity_errors.append(str(error))
        for path, expected in locked_data.items():
            try:
                need(fingerprint(Path(path)) == expected, 'dataset changed: ' + path)
            except Exception as error:
                integrity_errors.append(str(error))
        for row in receipt['generated_before_RTL']:
            try:
                need(fingerprint(inside(out, row['path'])) == {k: row[k] for k in ('bytes', 'sha256')},
                     'generated numeric input changed: ' + row['path'])
            except Exception as error:
                integrity_errors.append(str(error))
        receipt['source_data_numeric_SHA_reverified_after_run'] = not integrity_errors
        if integrity_errors:
            receipt['status'] = 'FAIL_INPUT_INTEGRITY'
            receipt['integrity_errors'] = integrity_errors
        receipt['outputs'] = [row for directory in (out / 'numeric', out / 'framework', out / 'results')
                              if directory.exists() for row in inventory(directory)
                              if row['path'] != 'results/run-receipt.json']
        receipt['ended_utc'] = now()
        save()
    print(json.dumps({'status': receipt['status'], 'receipt': str(receipt_path),
        'fixtures': len(receipt['fixture_checks']), 'failure': receipt.get('failure'),
        'product_quality_accepted': False}, ensure_ascii=False), flush=True)
    return 0 if receipt['status'].startswith('PASS_') else 1


if __name__ == '__main__':
    sys.exit(main())
