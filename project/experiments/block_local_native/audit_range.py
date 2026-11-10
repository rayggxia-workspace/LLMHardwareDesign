"""Offline immutable source/log audit. Does not run RTL on the workstation."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import tarfile


def unpack(root, row, kind):
    raw = base64.b64decode((root / row[kind + '_archive']).read_bytes(), validate=True)
    assert hashlib.sha256(raw).hexdigest() == row[kind + '_sha256']
    with tarfile.open(fileobj=io.BytesIO(raw), mode='r:gz') as archive:
        members = archive.getmembers()
        assert all((m.isfile() or m.isdir()) and not PurePosixPath(m.name).is_absolute() and
                   '..' not in PurePosixPath(m.name).parts for m in members)
        return {m.name: archive.extractfile(m).read() for m in members if m.isfile()}


def audit(root):
    rows = []
    for r in json.loads((root / 'index.json').read_text(encoding='utf-8'))['runs']:
        src, logs = unpack(root, r, 'source'), unpack(root, r, 'receipts')
        assert src['source/source-commit.txt'].decode().strip() == r['source_commit']
        manifest = json.loads(logs['receipts-manifest.json'])
        for path, sha in manifest.items():
            assert hashlib.sha256(logs[path]).hexdigest() == sha
        for line in logs['source.sha256'].decode().splitlines():
            sha, path = line.split('  ', 1)
            assert hashlib.sha256(src['source/' + path]).hexdigest() == sha
            assert src['source/' + path] == logs['source/' + path]
        results = [json.loads(v) for k, v in logs.items() if k.endswith('/result.json')]
        assert len(results) == 6 and {x['seed'] for x in results} == set(range(25001, 25007))
        for result in results:
            prefix = 'seed-' + str(result['seed']) + '/'
            for name, sha in result['hashes'].items():
                assert hashlib.sha256(logs[prefix + name]).hexdigest() == sha
            assert b'%Warning' not in logs[prefix + 'build.log']
            assert {v['initial'] for v in result['results']} == {0, 1, 2}
            for v in result['results']:
                assert logs[prefix + 'initial-' + str(v['initial']) + '.log'].decode().strip() == v['receipt']
                capacity = 6 if b'reg [5:0] tickets;' in src['source/project/rtl/block_local_native/record_range_iterator.sv'] else 4
                assert v['receipt'].startswith('PASS range ') and f'peak_tickets={capacity}' in v['receipt']
                if 'cases=144' in v['receipt']:
                    assert 'cases=144' in v['receipt'] and 'tails=254 invalid=12' in v['receipt']
        rows.append(dict(job=r['job'], source_commit=r['source_commit'], seeds=6, initial_states=3))
    return dict(passed=True, runs=rows, qualification='LC record-range ticket/address unit; not native M, program, real S, or physical qualification')


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--root', type=Path, required=True)
    print(json.dumps(audit(p.parse_args().root)))
