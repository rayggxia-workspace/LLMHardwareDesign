"""Bounded A8 + unchanged N/F8 regression, inside one Slurm allocation.

Python3.6+ standard library. No SSH, installation, source rewriting or sbatch.
The job preparer can launch this entire process inside the verified container;
then version checks, compilation and simulation all share its toolchain.
All builds/simulations are sequential, --threads1, explicit allocation-limited-j.
"""
import argparse
import collections
import datetime
import hashlib
import json
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path, PurePosixPath

ALLOWED = Path('/public/home/yuzelu/Melodydt')
NATIVE = '707878621b2add4ed218b8c43df2e95c9a56e2ba'
PROFILE_KEYS = {'n', 'f8', 'a8'}


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def fingerprint(path):
    size = path.stat().st_size
    sha = hashlib.sha256()
    blob = hashlib.sha1(b'blob ' + str(size).encode() + b'\0')
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            sha.update(data)
            blob.update(data)
    return {'bytes': size, 'sha256': sha.hexdigest(), 'git_blob_sha1': blob.hexdigest()}


def inside(path, root):
    path, root = path.resolve(), root.resolve()
    return path == root or root in path.parents


def source_path(root, relative):
    rel = PurePosixPath(relative)
    if rel.is_absolute() or '..' in rel.parts or not rel.parts:
        raise ValueError('source path must be repository-relative: ' + relative)
    result = (root / Path(*rel.parts)).resolve()
    if not inside(result, root) or not result.is_file():
        raise ValueError('missing source or symlink outside checkout: ' + relative)
    return result


def parse_output(text, expected_ids, marker, return_code):
    # Both plain Verilator output and retained ModelSim '# ' lines accepted.
    lines = [re.sub(r'^\s*#\s?', '', line).strip() for line in text.splitlines()]
    observed = []
    markers = []
    failures = []
    for line in lines:
        case = re.fullmatch(r'CASE_PASS ([A-Z][A-Z0-9_]+)', line)
        if case:
            observed.append(case.group(1))
        if re.match(r'^' + re.escape(marker) + r'(?:\s|$)', line):
            markers.append(line)
        if re.search(r'FAIL_(?:W[0-9]+|A8|P2)|%Error|%Fatal|\*\*\s*Fatal|Assertion failed|Aborting|core dumped', line):
            failures.append(line)
    repeated = sorted(k for k, v in collections.Counter(observed).items() if v != 1)
    missing = sorted(set(expected_ids) - set(observed))
    unexpected = sorted(set(observed) - set(expected_ids))
    summary_count = None
    if len(markers) == 1:
        count = re.search(r'(?:^|\s)cases=(\d+)(?:\s|$)', markers[0])
        if count:
            summary_count = int(count.group(1))
    passed = (return_code == 0 and not failures and len(markers) == 1 and
              summary_count == len(expected_ids) and not repeated and
              not missing and not unexpected and len(observed) == len(expected_ids))
    return {'passed': passed, 'expected_case_count': len(expected_ids),
            'observed_case_ids': observed, 'missing': missing, 'unexpected': unexpected,
            'duplicates': repeated, 'final_markers': markers,
            'summary_case_count': summary_count, 'failure_lines': failures}


def validate_inputs(root, contract, a8_contract, suite):
    baseline = json.loads(contract.read_text(encoding='utf8'))
    if baseline['native_source'] != NATIVE:
        raise ValueError('unexpected selected native source')
    lock_path = source_path(root, baseline['native_lock_path'])
    if fingerprint(lock_path)['sha256'] != baseline['native_lock_sha256']:
        raise ValueError('native lock file changed')
    lock = json.loads(lock_path.read_text(encoding='utf8'))
    if lock['selected_PR144_ref'] != NATIVE or len(lock['core_files']) != 14:
        raise ValueError('native14 lock mismatch')
    source_records = [(baseline['native_lock_path'], fingerprint(lock_path), 'native_lock')]
    for item in lock['core_files']:
        path = source_path(root, item['path'])
        actual = fingerprint(path)
        if actual['sha256'] != item['sha256'] or actual['git_blob_sha1'] != item['sha']:
            raise ValueError('native bytes mismatch: ' + item['path'])
        source_records.append((item['path'], actual, 'locked_native'))
    for item in baseline['common_rtl']:
        path = source_path(root, item['path'])
        actual = fingerprint(path)
        if actual['sha256'] != item['sha256']:
            raise ValueError('unchanged baseline RTL changed: ' + item['path'])
        source_records.append((item['path'], actual, 'unchanged_controller'))
    profiles = dict(baseline['profiles'])
    if a8_contract:
        entry = json.loads(a8_contract.read_text(encoding='utf8'))
        if entry.get('frozen') is not True or entry.get('profile_id') != 'a8':
            raise ValueError('A8 complete CASE/source contract not frozen')
        profiles['a8'] = entry
    keys = ['n', 'f8'] if suite == 'regression' else ['n', 'f8', 'a8'] if suite == 'all' else [suite]
    selected = []
    for key in keys:
        if key not in profiles:
            raise ValueError('A8 contract required for a8/all; do not silently drop A8')
        item = profiles[key]
        ids = item['expected_case_ids']
        if not ids or len(ids) != len(set(ids)) or not all(re.fullmatch(r'[A-Z][A-Z0-9_]+', x) for x in ids):
            raise ValueError('invalid complete expected CASE set: ' + key)
        if key in ('n', 'f8'):
            prior = item['acceptance_source']
            prior_path = source_path(root, prior['path'])
            if fingerprint(prior_path)['sha256'] != prior['sha256']:
                raise ValueError('prior complete CASE evidence changed: ' + key)
            prior_data = json.loads(prior_path.read_text(encoding='utf8'))
            if ids != prior_data['case_ids'] or len(ids) != {'n': 29, 'f8': 25}[key]:
                raise ValueError('do not remove prior regression/fault cases: ' + key)
        else:
            prior = item['acceptance_source']
            prior_path = source_path(root, prior['path'])
            if fingerprint(prior_path)['sha256'] != prior['sha256']:
                raise ValueError('independent A8 CASE contract changed')
            prior_data = json.loads(prior_path.read_text(encoding='utf8'))
            if (prior_data.get('status') != 'FROZEN_CASE_REQUIREMENTS_NOT_RTL_EXECUTION' or
                    ids != prior_data['expected_case_ids'] or
                    len(ids) != prior_data['expected_unique_case_count'] or
                    item['top_module'] != prior_data['top_module'] or
                    item['tb_path'] != prior_data['tb_path'] or
                    item['tb_sha256'] != prior_data['tb_sha256'] or
                    item['pass_marker'] != prior_data['pass_marker']):
                raise ValueError('A8 profile differs from independent complete CASE/source contract')
        source_records.append((prior['path'], fingerprint(prior_path), 'independent_complete_case_source_' + key))
        if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', item['top_module']):
            raise ValueError('invalid top module')
        tb = source_path(root, item['tb_path'])
        if fingerprint(tb)['sha256'] != item['tb_sha256']:
            raise ValueError('reviewed TB bytes changed: ' + item['tb_path'])
        selected.append((key, item))
        source_records.append((item['tb_path'], fingerprint(tb), 'testbench_' + key))
        for extra in item.get('extra_rtl_paths', []):
            if not isinstance(extra, dict) or set(extra) != {'path', 'sha256'}:
                raise ValueError('extra RTL requires explicit path/SHA')
            path = source_path(root, extra['path'])
            if fingerprint(path)['sha256'] != extra['sha256']:
                raise ValueError('A8 RTL bytes changed: ' + extra['path'])
            source_records.append((extra['path'], fingerprint(path), 'new_RTL_' + key))
        for relative in item.get('input_paths', []):
            path = source_path(root, relative)
            actual = fingerprint(path)
            expected = item.get('input_sha256', {}).get(relative)
            if expected and actual['sha256'] != expected:
                raise ValueError('reference input bytes changed: ' + relative)
            source_records.append((relative, actual, 'reference_input_' + key))
    seen = {}
    for relative, actual, scope in source_records:
        if relative in seen and seen[relative][0] != actual:
            raise ValueError('source changed while validating: ' + relative)
        seen[relative] = (actual, scope)
    return baseline, selected, [(p, x[0], x[1]) for p, x in seen.items()]


def terminate_group(process):
    if process.poll() is not None:
        return
    os.killpg(process.pid, signal.SIGTERM)
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--contract', type=Path, required=True)
    parser.add_argument('--a8-contract', type=Path)
    parser.add_argument('--suite', choices=['n', 'f8', 'a8', 'regression', 'all'], required=True)
    parser.add_argument('--name-initials', required=True)
    parser.add_argument('--source-ref', required=True)
    parser.add_argument('--verilator', default='verilator')
    parser.add_argument('--container-image', type=Path)
    parser.add_argument('--container-sha256')
    parser.add_argument('--build-jobs', type=int, default=1)
    parser.add_argument('--node-class', choices=['c64', 'c96', 'debug'], required=True)
    parser.add_argument('--job-wall-minutes', type=int, required=True)
    parser.add_argument('--build-timeout', type=int, default=1200)
    parser.add_argument('--sim-timeout', type=int, default=180)
    args = parser.parse_args()
    root, output = args.root.resolve(), args.output.resolve()
    if os.name != 'posix' or not inside(root, ALLOWED) or not inside(output, ALLOWED):
        parser.error('actual execution requires Linux root/output within ' + str(ALLOWED))
    for path in [args.contract, args.a8_contract] if args.a8_contract else [args.contract]:
        if not inside(path, ALLOWED):
            parser.error('contracts must also be within Melodydt directory')
    if not re.fullmatch(r'[a-z][a-z0-9]{1,19}', args.name_initials):
        parser.error('supply actual owner name abbreviation; no guessed default')
    if not re.fullmatch(r'[0-9a-fA-F]{40}', args.source_ref):
        parser.error('--source-ref requires full actual40-character research commit')
    if not os.environ.get('SLURM_JOB_ID') or int(os.environ.get('SLURM_NTASKS', '1')) != 1:
        parser.error('run only within one explicitly allocated Slurm task')
    job_name = os.environ.get('SLURM_JOB_NAME', '')
    if not job_name.startswith(args.name_initials + '-'):
        parser.error('actual Slurm job name must start with supplied owner initials plus -')
    allocated = int(os.environ.get('SLURM_CPUS_PER_TASK', '0'))
    affinity = len(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else allocated
    if not 1 <= args.build_jobs <= min(allocated, affinity):
        parser.error('build jobs must fit actual SLURM_CPUS_PER_TASK and affinity')
    if args.job_wall_minutes < 1 or (args.node_class == 'debug' and args.job_wall_minutes > 30):
        parser.error('debug time must not exceed30min')
    if args.build_timeout <= 0 or args.sim_timeout <= 0:
        parser.error('phase timeouts must be positive')
    if args.container_image:
        if not inside(args.container_image, Path('/public/home/yuzelu/opt')):
            parser.error('use explicit approved existing image under /public/home/yuzelu/opt')
        if not re.fullmatch(r'[0-9a-fA-F]{64}', args.container_sha256 or ''):
            parser.error('container SHA must be computed inside allocated job, not invented')
        if not (os.environ.get('SINGULARITY_CONTAINER') or os.environ.get('APPTAINER_CONTAINER')):
            parser.error('container mode requires entire runner already inside Singularity/Apptainer')
    if output.exists() and any(output.iterdir()):
        parser.error('use new/empty output; never overwrite previous attempts')
    output.mkdir(parents=True, exist_ok=True)
    for name in ['source', 'build', 'logs', 'tmp', 'results']:
        (output / name).mkdir()
    receipt_path = output / 'results/run-receipt.json'
    receipt = {'schema_version': 1, 'started_at_utc': now(), 'status': 'STARTING',
               'runner_argv': sys.argv,
               'source_ref': args.source_ref, 'native_source': NATIVE,
               'source_state': 'exact snapshots bind new/uncommitted source; source_ref is supplied base, not invented delivery commit',
               'suite': args.suite, 'owner_name_initials': args.name_initials,
               'host': {'node': platform.node(), 'python': sys.version},
               'slurm': {k: os.environ.get(k) for k in ['SLURM_JOB_ID', 'SLURM_JOB_NAME', 'SLURM_JOB_NODELIST', 'SLURM_CPUS_PER_TASK', 'SLURM_NTASKS', 'SLURM_JOB_PARTITION', 'SLURM_JOB_END_TIME']},
               'resources': {'declared_node_class': args.node_class, 'allocated_cpus_per_task': allocated,
                             'affinity_cpus': affinity, 'build_jobs': args.build_jobs,
                             'simulation_threads': 1, 'suites_execute_sequentially': True},
               'scope': {'actual_RTL_started': False, 'physical': False, 'whole_model': False,
                         'SSH_or_install_or_sbatch_by_runner': False},
               'inputs': [], 'commands': [], 'tools': {}, 'profiles': []}
    if args.container_image:
        receipt['container'] = {'image': str(args.container_image),
                                'image_sha256_computed_by_allocated_job': args.container_sha256,
                                'bytes': args.container_image.stat().st_size,
                                'environment_image': os.environ.get('SINGULARITY_CONTAINER') or os.environ.get('APPTAINER_CONTAINER'),
                                'entire_runner_build_and_simulation_inside': True,
                                'VERILATOR_ROOT': os.environ.get('VERILATOR_ROOT')}
    environment = dict(os.environ)
    for key in ['MAKEFLAGS', 'MFLAGS']:
        environment.pop(key, None)
    environment.update({'TMPDIR': str(output / 'tmp'), 'TMP': str(output / 'tmp'),
                        'TEMP': str(output / 'tmp'), 'OMP_NUM_THREADS': '1',
                        'CCACHE_DISABLE': '1', 'CCACHE_DIR': str(output / 'tmp/ccache'),
                        'CCACHE_TEMPDIR': str(output / 'tmp/ccache-tmp'),
                        'XDG_CACHE_HOME': str(output / 'tmp/cache')})
    deadline = time.monotonic() + args.job_wall_minutes * 60 - 30
    if os.environ.get('SLURM_JOB_END_TIME', '').isdigit():
        deadline = min(deadline, time.monotonic() + int(os.environ['SLURM_JOB_END_TIME']) - time.time() - 30)

    def save():
        receipt_path.write_bytes((json.dumps(receipt, ensure_ascii=False, indent=2) + '\n').encode('utf8'))

    def run(label, argv, timeout):
        remaining = int(deadline - time.monotonic())
        if remaining < 1:
            raise RuntimeError('job wall-time reserve reached before ' + label)
        log = output / 'logs' / (label + '.log')
        entry = {'label': label, 'argv': [str(x) for x in argv], 'cwd': str(output),
                 'started_at_utc': now(), 'timeout_seconds': min(timeout, remaining)}
        process = None
        caught = None
        with log.open('wb') as stream:
            try:
                process = subprocess.Popen(entry['argv'], cwd=str(output), stdout=stream,
                                           stderr=subprocess.STDOUT, env=environment, start_new_session=True)
                process.wait(timeout=entry['timeout_seconds'])
            except BaseException as error:
                caught = error
                if process:
                    terminate_group(process)
        entry.update({'finished_at_utc': now(), 'exit_code': process.returncode if process else None,
                      'log': str(log.relative_to(output)), 'log_fingerprint': fingerprint(log)})
        if caught:
            entry['execution_exception'] = type(caught).__name__ + ': ' + str(caught)
        receipt['commands'].append(entry)
        save()
        if caught:
            raise caught
        if process.returncode:
            raise RuntimeError(label + ' exited ' + str(process.returncode) + '; retained log')
        return log.read_text(encoding='utf8', errors='replace')

    def interrupted(number, frame):
        raise InterruptedError('received signal ' + str(number))

    signal.signal(signal.SIGTERM, interrupted)
    signal.signal(signal.SIGINT, interrupted)
    save()
    try:
        baseline, selected, inputs = validate_inputs(root, args.contract, args.a8_contract, args.suite)
        for path in [args.contract, args.a8_contract, Path(__file__)] if args.a8_contract else [args.contract, Path(__file__)]:
            receipt['inputs'].append(dict(fingerprint(path), path=str(path.resolve()), scope='execution_contract_or_script'))
        compile_paths = []
        include_dirs = set()
        input_map = {}
        for relative, actual, scope in inputs:
            source = source_path(root, relative)
            destination = output / 'source' / Path(*PurePosixPath(relative).parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())
            if fingerprint(destination) != actual:
                raise RuntimeError('source changed while snapshotting: ' + relative)
            receipt['inputs'].append(dict(actual, path=relative, snapshot=str(destination.relative_to(output)), scope=scope))
            input_map[relative] = destination
            if destination.suffix == '.svh':
                include_dirs.add(destination.parent)
            elif destination.suffix == '.sv':
                compile_paths.append(destination)
                include_dirs.add(destination.parent)
        tool = shutil.which(args.verilator)
        if not tool:
            raise RuntimeError('Verilator executable unavailable; version/compatibility unverified')
        tool = Path(tool).resolve()
        receipt['tools']['verilator'] = dict(fingerprint(tool), path=str(tool))
        version = run('verilator-version', [tool, '--version'], 30).strip()
        receipt['tools']['verilator']['version'] = version
        match = re.search(r'Verilator\s+(\d+)\.(\d+)', version)
        if not match or int(match.group(1)) < 5:
            raise RuntimeError('need actual Verilator5+ binary/timing support; do not install or skip tests')
        for name, executable in [('compiler', os.environ.get('CXX', 'c++')), ('make', 'make')]:
            resolved = shutil.which(executable)
            if not resolved:
                raise RuntimeError(name + ' tool unavailable')
            receipt['tools'][name] = dict(fingerprint(Path(resolved).resolve()), path=resolved,
                                          version=run(name + '-version', [resolved, '--version'], 30).splitlines()[0])
        save()
        for key, item in selected:
            build = output / 'build' / key
            build.mkdir()
            top = item['top_module']
            selected_tbs = {x['tb_path'] for _, x in selected}
            files = [p for p in compile_paths if str(p.relative_to(output / 'source')).replace('\\', '/') not in selected_tbs or p == input_map[item['tb_path']]]
            argv = [tool, '--binary', '--timing', '--assert', '--threads', '1',
                    '-j', str(args.build_jobs), '--top-module', top,
                    '--Mdir', build, '-o', top, '--language', '1800-2017']
            argv += ['-I' + str(x) for x in sorted(include_dirs)]
            argv += files
            # No bbox-unsup/no-timing/no-assert/faultcase filtering/warning suppression.
            run('build-' + key, argv, args.build_timeout)
            executable = build / top
            if not executable.is_file():
                raise RuntimeError('missing generated simulator ' + str(executable))
            receipt['scope']['actual_RTL_started'] = True
            result = {'profile': key, 'top_module': top, 'binary': dict(fingerprint(executable), path=str(executable.relative_to(output))),
                      'expected_case_ids': item['expected_case_ids'], 'pass_marker': item['pass_marker']}
            receipt['profiles'].append(result)
            text = run('simulate-' + key, [executable], args.sim_timeout)
            result['output_check'] = parse_output(text, item['expected_case_ids'], item['pass_marker'], 0)
            save()
            if not result['output_check']['passed']:
                raise RuntimeError('missing/extra/duplicate CASE or PASS/failure mismatch for ' + key)
        receipt['status'] = 'PASS_REAL_VERILATOR_RTL_DECLARED_CASES'
    except BaseException as error:
        receipt['status'] = 'FAILED_OR_BLOCKED_NOT_ACCEPTED'
        receipt['failure'] = {'kind': type(error).__name__, 'message': str(error)}
        raise
    finally:
        receipt['finished_at_utc'] = now()
        save()
    print('PASS declared complete CASE sets: ' + str(receipt_path), flush=True)


if __name__ == '__main__':
    main()
