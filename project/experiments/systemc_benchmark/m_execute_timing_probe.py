"""Check independently clocked M execution resources against real descriptor grid.

This covers valid non-stalled resident commands only. Existing native tests
check exact S64 payload arithmetic; this model never reads their cycle totals.
No LC/feeder/memory, full-model time or energy acceptance is implied.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from m_profile import KEYS, TIMES, load_grid


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    for name in ('executable', 'grid', 'output'):
        p.add_argument(name, type=Path)
    p.add_argument('--native-receipt', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(exist_ok=False)
    qualified = json.loads(a.native_receipt.read_text())
    if qualified.get('descriptor_count') != 8192 or not qualified.get('identical_timings') or any(
            not x.get('exact_s64_passed') or x.get('descriptors_checked') != 8192
            for x in qualified.get('functional_summaries', [])) or len(qualified.get('functional_summaries', [])) != 3:
        raise ValueError('qualified three-initialization native receipt required')
    native_inputs = []
    for name, expected in qualified['files_sha256'].items():
        basename = name.replace('\\', '/').split('/')[-1]
        path = a.grid/basename
        if not path.is_file():
            path = a.grid.parent/basename
        if sha(path) != expected:
            raise ValueError('native evidence input drift: '+basename)
        native_inputs.append(path)
    paths = [a.grid/('profile-'+s+'.jsonl') for s in ('1-143', '2-143', '2-144')]
    grid = load_grid(paths)
    keys = sorted(grid)
    inputs = a.output/'descriptors.tsv'
    inputs.write_text(''.join(' '.join(map(str,k))+'\n' for k in keys))
    log = a.output/'systemc.log'
    with log.open('wb') as stream:
        subprocess.run([str(a.executable), str(inputs)], stdout=stream, stderr=subprocess.STDOUT, check=True)
    measured = {}
    for line in log.read_text().splitlines():
        if line.startswith('ROW '):
            _, index, *values = line.split()
            if int(index) in measured or len(values) != 3:
                raise ValueError('duplicate or malformed modeled descriptor')
            measured[int(index)] = tuple(map(int, values))
    if set(measured) != set(range(len(keys))):
        raise ValueError('incomplete modeled descriptors')
    failures = [{'descriptor': dict(zip(KEYS,k)), 'actual_native': dict(zip(TIMES,grid[k])),
                 'modeled': dict(zip(TIMES,measured[i]))}
                for i,k in enumerate(keys) if measured[i] != grid[k]]
    negatives = []
    for i, descriptor in enumerate(((0, 0, 0, 1, 1, 1), (0, 0, 1, 5, 1, 1),
            (2, 0, 1, 1, 1, 1), (0, 0, 1, 1, 0, 1), (0, 0, 1, 1, 1, 9))):
        path = a.output/('invalid-%d.tsv'%i)
        path.write_text(' '.join(map(str,descriptor))+'\n')
        run = subprocess.run([str(a.executable), str(path)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        (a.output/('invalid-%d.log'%i)).write_bytes(run.stdout+run.stderr)
        if not run.returncode or b'unsupported native descriptor' not in run.stderr:
            raise ValueError('unsupported shape was not rejected')
        negatives.append({'descriptor': list(descriptor), 'rejected': True})
    result = {'scope': __doc__, 'descriptor_count': len(keys),
        'three_native_initializations_equal': True, 'different_count': len(failures),
        'first_differences': failures[:20], 'passed': not failures,
        'model_input_contains_no_measured_latency': True,
        'clock_hz': 300000000, 'SystemC_version': '3.0.1',
        'unsupported_descriptors': negatives,
        'inputs_sha256': {str(path):sha(path) for path in native_inputs+[a.native_receipt, a.executable,
            inputs, Path(__file__), Path(__file__).with_name('systemc_m_execute.cpp')]},
        'full_model_timing_qualified': False, 'total_energy_qualified': False}
    (a.output/'receipt.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'descriptor_count': len(keys), 'different_count': len(failures), 'passed': not failures}))
    if failures:
        raise ValueError('independent M execution model differs from accepted native grid')


if __name__ == '__main__':
    main()
