"""Read-only source, strict build and scoreboard receipt audit; no simulation."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile


def unpack(root, row, kind):
    if row.get(kind + '_parts'):
        pieces = []
        for part in row[kind + '_parts']:
            raw = (root / part['path']).read_bytes()
            assert len(raw) == part['bytes'] and hashlib.sha256(raw).hexdigest() == part['sha256']
            pieces.append(raw)
        encoded = b''.join(pieces)
        assert hashlib.sha256(encoded).hexdigest() == row['base64_reassembly_sha256']
    else:
        encoded = (root / row[kind + '_archive']).read_bytes()
    data = base64.b64decode(encoded, validate=True)
    assert hashlib.sha256(data).hexdigest() == row[kind + '_sha256']
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as t:
        members = t.getmembers()
        assert all((m.isfile() or m.isdir()) and not PurePosixPath(m.name).is_absolute() and
                   '..' not in PurePosixPath(m.name).parts for m in members)
        return {m.name: t.extractfile(m).read() for m in members if m.isfile()}


def audit(root):
    rows = []
    for r in json.loads((root / 'index.json').read_text(encoding='utf-8'))['runs']:
        src, logs = unpack(root, r, 'source'), unpack(root, r, 'receipts')
        assert src['source/source-commit.txt'].decode().strip() == r['source_commit']
        for line in logs['source.sha256'].decode().splitlines():
            expected, name = line.split('  ', 1)
            assert hashlib.sha256(src['source/' + name]).hexdigest() == expected
        results = [json.loads(data) for name, data in logs.items() if name.endswith('/result.json')]
        if r['state'] == 'COMPLETED':
            assert len(results) == 6 and {v['seed'] for v in results} == set(range(25001, 25007))
            for v in results:
                prefix = 'seed-' + str(v['seed']) + '/'
                for p in ['build.log', 'simulation.log', 'counts.vh']:
                    assert hashlib.sha256(logs[prefix + p]).hexdigest() == v['hashes'][p]
                assert b'%Warning' not in logs[prefix + 'build.log']
                assert b'PASS context ' in logs[prefix + 'simulation.log']
                assert v['counts']['numeric_fault'] >= 16 and v['counts']['restore'] >= 274
                if 'scale_vectors' in v:
                    for p in ['scale-build.log', 'scale-simulation.log', 'scale.hex']:
                        assert hashlib.sha256(logs[prefix + p]).hexdigest() == v['hashes'][p]
                    assert b'%Warning' not in logs[prefix + 'scale-build.log']
                    assert b'PASS scale ' in logs[prefix + 'scale-simulation.log']
                    assert v['scale_vectors'] > 4000 and v['scale_good'] > 1000
                    assert b'cycle-accepted_cycle[received]<3' in src['source/project/experiments/w8a16_context/tb_context.sv']
        else:
            assert not results and b'context mismatch 20' in logs['seed-25001/simulation.log']
        rows.append(dict(job=r['job'], state=r['state'], seeds=len(results), commands=sum(v['vectors'] for v in results)))
    return dict(passed=True, runs=rows, qualification='finite RF unit receipts only; numeric replay/physical acceptance not performed by this auditor')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    print(json.dumps(audit(p.parse_args().root)))
