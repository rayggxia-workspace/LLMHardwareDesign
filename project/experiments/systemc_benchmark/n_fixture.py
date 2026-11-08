"""Captured-derived S16 samples with old independent N reference answers.

Factor values also use Python integer arithmetic/isqrt as an independent check.
This does not establish a distribution representative of all N model commands.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('operands', type=Path)
    p.add_argument('oracle_command', type=json.loads)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    if not isinstance(a.oracle_command, list) or not all(isinstance(x, str) for x in a.oracle_command):
        raise ValueError('oracle command must be a structured argument list')
    rows = [list(map(int, s.split())) for s in a.operands.read_text().splitlines()]
    if len(rows) != 72 or any(len(x) != 3 for x in rows):
        raise ValueError('expected three cohorts of 24 captured components')
    a.output.mkdir(exist_ok=False)
    proc = subprocess.Popen(a.oracle_command, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    records = []
    try:
        for cohort in range(3):
            captured = [x[0] for x in rows[cohort*24:(cohort+1)*24]]
            for label, mode in [('rms', 1), ('l2', 2), ('exp', 0)]:
                lines = []
                vectors = [captured] if mode == 1 else [[x] for x in captured]
                for values in vectors:
                    kind = 4 if mode == 1 else 6 if mode == 2 else 5
                    data = struct.pack('<III', kind, len(values), 1)
                    data += struct.pack('<' + 'h'*len(values), *values)
                    proc.stdin.write(data); proc.stdin.flush()
                    answer = proc.stdout.read(4)
                    if len(answer) != 4:
                        raise ValueError('old independent N oracle failed')
                    expected, = struct.unpack('<I', answer)
                    if mode:
                        sq = sum(x*x for x in values) << 16
                        if mode == 1:
                            sq //= len(values)
                        independent = (1 << 38) // math.isqrt(sq + (1 << 16))
                        if independent != expected:
                            raise ValueError('independent factor formula and old oracle disagree')
                    lines.append(' '.join(map(str, [mode, 1, len(values), expected, *values])))
                path = a.output / ('cohort-%d-%s.tsv' % (cohort, label))
                path.write_text('\n'.join(lines) + '\n')
                records.append({'cohort': cohort, 'service': label, 'file': path.name,
                                'fixture_sha256': sha(path), 'services_per_batch': len(vectors)})
    finally:
        proc.stdin.close()
        if proc.wait() != 0:
            raise ValueError('independent oracle returned error')
    (a.output / 'receipt.json').write_text(json.dumps({'source_sha256': sha(Path(__file__)),
        'operands_sha256': sha(a.operands), 'oracle_command': a.oracle_command,
        'records': records, 'whole_workload_qualified': False}, indent=2) + '\n')


if __name__ == '__main__':
    main()
