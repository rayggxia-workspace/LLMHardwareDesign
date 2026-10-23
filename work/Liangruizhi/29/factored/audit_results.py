"""Verify raw return integrity and compare full saved results to frozen baseline."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

BASE_SHA = 'f678cc7ed3ec88789fee88a234afd9a02c7bd3696ae51a2c3734680052a33d83'
RETURN_SHA = 'd25070997ac179c6d0d12b155b8627e95dba78340611a281659bc1dca2384548'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--baseline', required=True, type=Path)
    p.add_argument('--returned', required=True, type=Path)
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args()
    if a.out.exists():
        raise ValueError('refusing existing output')
    assert hashlib.sha256(a.baseline.read_bytes()).hexdigest() == BASE_SHA
    assert hashlib.sha256(a.returned.read_bytes()).hexdigest() == RETURN_SHA
    configs = cases = stress = traces = 0
    with zipfile.ZipFile(a.baseline) as base, zipfile.ZipFile(a.returned) as returned:
        manifest = json.loads(returned.read('return-manifest.json'))
        assert len(returned.namelist()) == len(set(returned.namelist())) == len(manifest)+1
        for name, expected in manifest.items():
            assert not Path(name).is_absolute() and '..' not in Path(name).parts
            raw = returned.read(name)
            assert len(raw) == expected['bytes'] and hashlib.sha256(raw).hexdigest() == expected['sha256']
        m = json.loads(returned.read('factored02/run-01/manifest.json'))
        assert m['source_bundle']['source_commit'] == '0d607f5ebc575764a62a7ebb14aba451f2f22748'
        assert m['failures'] == 0 and len(m['groups']) == 27
        for name in sorted(n for n in returned.namelist()
                           if n.startswith('factored02/run-01/') and n.endswith('/results.json')):
            old = name.replace('factored02/', 'run1/')
            x, y = json.loads(base.read(old)), json.loads(returned.read(name))
            assert x['config'] == y['config']
            for kind in ['cases', 'stress']:
                assert len(x[kind]) == len(y[kind])
                for original, actual in zip(x[kind], y[kind]):
                    assert original == actual
                    assert actual['exit_code'] == 0
                    traces += int('trace_sha256' in actual)
                if kind == 'cases':
                    cases += len(x[kind])
                else:
                    stress += len(x[kind])
            configs += 1
        assert (configs, cases, stress, traces) == (27, 1872, 54, 33)
        assert returned.read('factored02/synth/exit.txt').strip() == b'124'
        assert 'Exit status: 124' in returned.read('factored02/synth/frontend.time').decode()
    result = {'status': 'PASS', 'members_hashed': len(manifest), 'configurations': configs,
              'case_results_equal': cases, 'stress_results_equal': stress, 'saved_trace_hashes_equal': traces,
              'generic_synthesis': 'NOT COMPLETED: frontend limit 360s, exit124',
              'scope': 'saved-result/hash regression; not formal equivalence or independent full trace audit'}
    a.out.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result))


if __name__ == '__main__':
    main()
