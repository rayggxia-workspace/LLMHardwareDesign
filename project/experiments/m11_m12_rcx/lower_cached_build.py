"""Validate reusable physical indices against saved numerical results exactly."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

from native_scene import write

BASE = Path('/public/home/yuzelu/PingyangHuang')
REFERENCE = BASE / 'issue-222-lower-pair-refinement-build-TirIyl0c/job-100849-0/result'
ACCEPTED = BASE / 'issue-222-lower-origin-control-perms-ktefURj0/job-100765-0/result'
LOCAL = BASE / 'issue-222-lower-local-lru-MUd9kGtR/job-100779-0/result'
REAL = BASE / 'issue-222-lower-pair-native-checked-JSZ4nNjx/job-100812-0/result'
TILES = BASE / 'issue-222-lower-children-tiles-yPao4MaK/job-100802-0/result'
HEADERS = Path('/public/home/yuzelu/opt/eda/llhd-fsv-i121-block-v1-20261027-099/src/fsv')


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def execute(command, out, name):
    start = time.monotonic()
    with (out / (name + '.jsonl')).open('xb') as f, (out / (name + '.log')).open('xb') as e:
        subprocess.run(list(map(str, command)), stdout=f, stderr=e, check=True)
    rows = [json.loads(line) for line in (out / (name + '.jsonl')).open()]
    return rows, time.monotonic() - start


def main():
    out = Path(os.environ['LOWER_OUT'])
    out.mkdir()
    src = Path(__file__).resolve().parent
    reference = json.loads((REFERENCE / 'build.json').read_text())
    assert reference['all_controls_passed'] and reference['confidence_budget_configurable']
    assert sha(REFERENCE / 'lower_paired_solver.cpp') == reference['instrumented_solver_sha256']
    shutil.copyfile(REFERENCE / 'lower_paired_solver.cpp', out / 'lower_paired_solver.cpp')
    for name in ['lower_pair_field.cpp', 'lower_cached_pair_field.cpp']:
        shutil.copyfile(src / name, out / name)
    objects = [Path(p) for p in reference['linked_objects']]
    assert all(sha(p) == reference['linked_objects'][str(p)] for p in objects)
    binary = out / 'lower_cached_pair_field'
    command = ['g++', '-std=c++20', '-O3', '-pthread', '-I' + str(ACCEPTED / 'include'),
               '-I' + str(HEADERS / 'include'), '-I' + str(HEADERS / 'src'),
               str(out / 'lower_cached_pair_field.cpp'), *map(str, objects), '-o', str(binary)]
    with (out / 'compile.log').open('xb') as f:
        subprocess.run(command, stdout=f, stderr=subprocess.STDOUT, check=True)
    threads = os.environ['LOWER_CPUS']
    checks = []
    names = ['split-one', 'split-many', 'single-owner', 'separate-neighbors',
             'common-potential', 'disjoint-near-equal-coordinates', 'added-upper']
    for name in names:
        tiles = REFERENCE / 'added-upper-tiles' if name == 'added-upper' else LOCAL / (name + '-tiles')
        options = (['262144', '1048576', '.125', '128', '128', '99991', '.01', '.05']
                   if name == 'added-upper' else ['4096', '262144', '.125', '32', '256', '99991', '.01', '.05'])
        rows, elapsed = execute([binary, tiles, tiles / 'masters.bin', threads, *options], out, name)
        old = [json.loads(line) for line in (REFERENCE / (name + '.jsonl')).open()]
        assert rows == old, ('Cached physical view changes result', name)
        checks.append(dict(case=name, all_numerical_fields_exact=True, elapsed_seconds=elapsed))
    prep = json.loads((TILES / 'prepare.json').read_text())
    geometry = Path(prep['geometry'])
    rows, elapsed = execute([binary, geometry, REAL / 'masters.bin', threads,
                             '4096', '262144', '.5', '32', '256', '104729', '.01', '.05'], out, 'real-native')
    old = [json.loads(line) for line in (REAL / 'native-pairs.jsonl').open()]
    assert rows == old, 'Real-native cached view differs from saved control'
    checks.append(dict(case='real-native-fifteen', all_numerical_fields_exact=True, elapsed_seconds=elapsed))
    fixture = out / 'two-targets.bin'
    write(fixture, ['N' + str(i) for i in range(2504)],
          [(2502, 1, [0, 0, 10, 2, 2, 12]), (2503, 1, [4, 0, 10, 6, 2, 12]),
           (0, 0, [0, 0, 12.5, 6, 2, 14.5])])
    tiles = out / 'two-targets-tiles'
    with (out / 'fixture-tile.log').open('xb') as f:
        subprocess.run([str(LOCAL / 'lower_tiles'), str(fixture), str(tiles), '32'],
                       stdout=f, stderr=subprocess.STDOUT, check=True)
    options = ['4096', '262144', '.5', '32', '256', '104729', '.01', '.05']
    old_rows, old_time = execute([REFERENCE / 'lower_pair_field', tiles, tiles / 'masters.bin', threads, *options], out, 'two-old')
    new_rows, new_time = execute([binary, tiles, tiles / 'masters.bin', threads, *options], out, 'two-cached')
    assert old_rows == new_rows and len(new_rows) == 2
    assert 'PHYSICAL_CACHE hits=1 ' in (out / 'two-cached.log').read_text(), 'No cross-target cache reuse exercised'
    checks.append(dict(case='two-distinct-targets-one-physical-index', all_numerical_fields_exact=True,
                       cache_reuse_exercised=True, old_seconds=old_time, cached_seconds=new_time))
    result = dict(binary=str(binary), binary_sha256=sha(binary), all_controls_passed=True,
                  cached_scene_view_exact=True, conditional_replay_verified_exact=True,
                  zero_hits_have_positive_uncertainty=True, confidence_budget_configurable=True,
                  compatible_input_binaries=[reference['binary_sha256'], *reference['compatible_input_binaries']],
                  controls=checks, linked_objects=reference['linked_objects'],
                  instrumented_solver_sha256=reference['instrumented_solver_sha256'],
                  reporter_source_sha256=sha(src / 'lower_cached_pair_field.cpp'),
                  paired_library_source_sha256=sha(src / 'lower_pair_field.cpp'),
                  cache_box_budget=2000000, maximum_cached_windows=8,
                  scope='Read-only physical scene reuse, uniform eps only. Target identities change via views; physical indices never mutate. Every saved numeric field remains exactly identical. Production replacement may touch unstarted elements only.')
    (out / 'build.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
