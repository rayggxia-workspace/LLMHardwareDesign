"""Build paired reporter; verify forced replay and existing field references."""
import hashlib
import argparse
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess

from native_scene import write

BASE = Path('/public/home/yuzelu/PingyangHuang')
ACCEPTED = BASE / 'issue-222-lower-origin-control-perms-ktefURj0/job-100765-0/result'
ORIGINAL = BASE / 'issue-222-merge-fix-OLZaDNeN/job-100237/build'
LOCAL = BASE / 'issue-222-lower-local-lru-MUd9kGtR/job-100779-0/result'
SOURCE = Path('/public/home/yuzelu/opt/eda/llhd-fsv-i121-block-v1-20261027-099')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(command, out, name, env=None):
    with (out / (name + '.jsonl')).open('xb') as stdout, (out / (name + '.log')).open('xb') as stderr:
        subprocess.run(list(map(str, command)), stdout=stdout, stderr=stderr, check=True, env=env)
    return json.loads((out / (name + '.jsonl')).read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-build', type=Path)
    options = parser.parse_args()
    out = Path(os.environ['LOWER_OUT'])
    out.mkdir()
    src = Path(__file__).resolve().parent
    threads = os.environ['LOWER_CPUS']
    proof = json.loads((ACCEPTED / 'build.json').read_text())
    assert proof['source_net_restricted_origin'] and proof['all_controls_passed']
    assert sha(ACCEPTED / 'Solver.cpp') == proof['patched_solver_sha256']
    source = (ACCEPTED / 'Solver.cpp').read_text()
    changes = [
        ('bool& left, int& bin, int& destination) const',
         'bool& left, int& bin, int& destination, bool* upper_query = nullptr) const'),
        ('    const auto origin = index_.nearest(p);',
         '    const auto origin = index_.nearest(p);\n'
         '    if(upper_query && origin.box >= 0 && Frame::shapeNet(geometry_,origin.box)==2) *upper_query=true;'),
        ('      const typename SpatialIndex<D>::Nearest n = index_.nearest(p);',
         '      const typename SpatialIndex<D>::Nearest n = index_.nearest(p);\n'
         '      if(upper_query && n.box >= 0 && Frame::shapeNet(geometry_,n.box)==2) *upper_query=true;'),
    ]
    for old, new in changes:
        assert source.count(old) == 1, old
        source = source.replace(old, new)
    (out / 'lower_paired_solver.cpp').write_text(source)
    shutil.copyfile(src / 'lower_pair_field.cpp', out / 'lower_pair_field.cpp')
    old = json.loads((ORIGINAL / 'build.json').read_text())
    objects = [ORIGINAL / 'GaussianSurface.o'] + [SOURCE / n for n in old['unchanged_objects']]
    assert all(sha(SOURCE / n) == h for n, h in old['unchanged_objects'].items())
    headers = SOURCE / 'src/fsv'
    command = ['g++', '-std=c++20', '-O3', '-pthread', '-I' + str(ACCEPTED / 'include'),
               '-I' + str(headers / 'include'), '-I' + str(headers / 'src'),
               str(out / 'lower_pair_field.cpp'), *map(str, objects), '-o', str(out / 'lower_pair_field')]
    with (out / 'compile.log').open('xb') as log:
        subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, check=True)
    controls = []
    binary = out / 'lower_pair_field'
    for name in ['split-one', 'split-many', 'single-owner', 'separate-neighbors',
                 'common-potential', 'disjoint-near-equal-coordinates']:
        tiles = LOCAL / (name + '-tiles')
        args = [binary, tiles, tiles / 'masters.bin', threads, '4096', '262144',
                '.125', '32', '256', '99991', '.01', '.05']
        row = run(args, out, name)
        forced = run(args, out, name + '-forced', env=dict(os.environ, LOWER_PAIR_FORCE_REPLAY='1'))
        assert {k: v for k, v in row.items() if k != 'replayed_before_walks'} == {
            k: v for k, v in forced.items() if k != 'replayed_before_walks'}, name
        assert row['delta_ff'] == 0 and row['before_ff'] == row['after_ff'], name
        reference = json.loads((LOCAL / (name + '.jsonl')).read_text())
        difference = abs(row['before_ff'] - reference['before_ff'])
        assert difference <= 5 * (row['before_sigma_ff'] + reference['before_sigma_ff']), name
        controls.append(dict(case=name, forced_replay_exact=True, unchanged_delta_exact_zero=True,
                             global_difference_ff=difference, paired_sigma_ff=row['before_sigma_ff'],
                             reference_sigma_ff=reference['before_sigma_ff'],
                             numerical_precision_passed=row['qualified_precision'],
                             reference_sha256=sha(LOCAL / (name + '.jsonl'))))
    # Strong, physically separated added upper conductor: includes both
    # changed and unchanged paths and therefore exercises conditional replay.
    fixture = out / 'added-upper.bin'
    write(fixture, ['N' + str(i) for i in range(2503)],
          [(2502, 1, [0, 0, 10, 2, 2, 12]), (0, 0, [0, 0, 12.5, 2, 2, 14.5])])
    tiles = out / 'added-upper-tiles'
    with (out / 'added-upper-tile.log').open('xb') as log:
        subprocess.run([str(LOCAL / 'lower_tiles'), str(fixture), str(tiles), '32'],
                       stdout=log, stderr=subprocess.STDOUT, check=True)
    args = [binary, tiles, tiles / 'masters.bin', threads, '262144', '1048576',
            '.125', '128', '128', '99991', '.01', '.05']
    row = run(args, out, 'added-upper')
    forced = run(args, out, 'added-upper-forced', env=dict(os.environ, LOWER_PAIR_FORCE_REPLAY='1'))
    assert {k: v for k, v in row.items() if k != 'replayed_before_walks'} == {
        k: v for k, v in forced.items() if k != 'replayed_before_walks'}
    assert 0 < row['replayed_before_walks'] < row['walks']
    assert row['delta_ff'] > 0 and row['full_delta_interval_low_ff'] > 0
    # Reuse old reporter on this new fixture for an independent algorithm path.
    reference = run([LOCAL / 'lower_local_field', tiles, tiles / 'masters.bin',
                     threads, '262144', '.125', '128', '128', '99991', '.002'],
                    out, 'added-upper-reference')
    for label in ['before', 'after']:
        assert abs(row[label + '_ff'] - reference[label + '_ff']) <= 5 * (
            row[label + '_sigma_ff'] + reference[label + '_sigma_ff']), label
    controls.append(dict(case='added-upper', forced_replay_exact=True,
                         delta_positive_and_interval_excludes_zero=True,
                         conditional_replay_fraction=row['replayed_before_walks'] / row['walks'],
                         numerical_precision_passed=row['qualified_precision']))
    compatible = []
    if options.reference_build:
        reference_build = json.loads((options.reference_build / 'build.json').read_text())
        assert reference_build['all_controls_passed']
        for name in [c['case'] for c in controls]:
            assert json.loads((out / (name + '.jsonl')).read_text()) == json.loads(
                (options.reference_build / (name + '.jsonl')).read_text()), ('Default reporting changed', name)
        compatible.append(reference_build['binary_sha256'])
    tighter_args = [binary, tiles, tiles / 'masters.bin', threads,
                    '262144', '1048576', '.125', '128', '128', '99991', '.01', '.01']
    tighter = run(tighter_args, out, 'added-upper-99-percent')
    assert tighter['per_net_confidence'] == .99
    assert tighter['full_delta_interval_high_ff'] - tighter['full_delta_interval_low_ff'] >= (
        row['full_delta_interval_high_ff'] - row['full_delta_interval_low_ff'])
    result = dict(binary=str(binary), binary_sha256=sha(binary),
                  compatible_input_binaries=compatible, confidence_budget_configurable=True,
                  accepted_solver=str(ACCEPTED / 'Solver.cpp'),
                  accepted_solver_sha256=sha(ACCEPTED / 'Solver.cpp'),
                  instrumented_solver_sha256=sha(out / 'lower_paired_solver.cpp'),
                  reporter_source_sha256=sha(src / 'lower_pair_field.cpp'),
                  linked_objects={str(p): sha(p) for p in objects},
                  controls=controls, all_controls_passed=True,
                  paired_common_surface=True, fixed_unbiased_control_variate_beta=.5,
                  conditional_replay_verified_exact=True, zero_hits_have_positive_uncertainty=True,
                  confidence_source='Maurer & Pontil 2009 Theorem 4, https://www.cs.mcgill.ca/~colt2009/papers/012.pdf',
                  qualification='Estimator and replay controls only. Real-native comparisons required. Per-net numerical intervals are not simultaneous physical/signoff guarantees.')
    (out / 'build.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
