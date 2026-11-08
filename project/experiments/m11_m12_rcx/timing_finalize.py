"""Collect only completed matching timing cases, without rerunning STA."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--roots', type=Path, nargs='+', required=True)
    p.add_argument('--readback-root', type=Path, required=True)
    p.add_argument('--cases', default='0,1,2,3,4,5,6,7')
    a = p.parse_args()
    expected = set(map(int, a.cases.split(',')))
    cases = {}
    for root in a.roots:
        for f in root.glob('job-*/result/timing.json'):
            meta = json.loads(f.read_text()); case = meta['case']
            if case not in expected: continue
            assert case not in cases, ('Duplicate completed case', case)
            cases[case] = f.parent
    assert set(cases) == expected, sorted(cases)
    subprocess.run([sys.executable, '-B', str(Path(__file__).with_name('timing_assess.py')),
                    '--runs', *[str(cases[k]) for k in sorted(cases)],
                    '--readback-root', str(a.readback_root),
                    '--out', str(Path(os.environ['TIMING_OUT']) / 'result')], check=True)


if __name__ == '__main__': main()
