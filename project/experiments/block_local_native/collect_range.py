"""Recover owned range run logs and pin their exact source and receipt bytes."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import subprocess

HOST = 'yuzelu@10.129.166.172'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--package-dir', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--family', choices=('range', 'quant', 'gscale', 'scaledir', 'context', 'scope', 'scopestream', 'copymeta', 'copy-a', 'scatter', 'gcopy-a', 'copywin', 'copylook', 'distmid', 'e32', 'ejoint', 'ffnmid'), default='range')
    p.add_argument('--receipt-cache', type=Path, help='Keep large raw receipts in owned remote storage and this exact local mirror; commit index/source only')
    a = p.parse_args()
    submission = json.loads((a.package_dir / 'submission.json').read_text(encoding='utf-8'))
    root = submission['remote_root']
    assert re.fullmatch(r'/public/home/yuzelu/project-circuit/issue250-' + a.family + r'-[0-9-]+', root)
    job = int(submission['submit'].split()[-1])
    state = subprocess.check_output(['ssh', '-o', 'BatchMode=yes', HOST,
        f'sacct -j {job} -X -n -P -o JobID,State,ExitCode,Elapsed,AllocCPUS']).decode().strip()
    fields = state.split('|')
    assert fields[0] == str(job) and fields[1] in ('COMPLETED', 'FAILED') and fields[4] == '60', state
    assert fields[1] != 'COMPLETED' or fields[2] == '0:0', state
    script = '''import hashlib,json,pathlib,tarfile
root=pathlib.Path(ROOT)
paths=[p for p in root.rglob('*') if p.is_file() and not any(s.endswith('obj') or s.startswith('obj-') for s in p.relative_to(root).parts[:-1]) and p.name not in ('source.tar.gz','receipts.tar.gz','receipts-manifest.json')]
manifest={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
(root/'receipts-manifest.json').write_text(json.dumps(manifest,indent=2)+'\\n')
with tarfile.open(root/'receipts.tar.gz','w:gz') as t:
 for p in paths+[root/'receipts-manifest.json']:t.add(p,arcname=str(p.relative_to(root)))
print(hashlib.sha256((root/'receipts.tar.gz').read_bytes()).hexdigest())
'''.replace('ROOT', repr(root))
    expected = subprocess.check_output(['ssh', '-o', 'BatchMode=yes', HOST,
        'python3 -c ' + shlex.quote(script)]).decode().strip()
    receipt = a.package_dir / 'receipts.tar.gz'
    subprocess.run(['scp', '-q', HOST + ':' + root + '/receipts.tar.gz', str(receipt)], check=True)
    assert hashlib.sha256(receipt.read_bytes()).hexdigest() == expected
    source = a.package_dir / 'source.tar.gz'
    assert hashlib.sha256(source.read_bytes()).hexdigest() == submission['package_sha256']
    a.out.mkdir(parents=True, exist_ok=True)
    files = {}
    for kind, data in [('source', source.read_bytes()), ('receipts', receipt.read_bytes())]:
        if kind == 'receipts' and a.receipt_cache is not None:
            a.receipt_cache.mkdir(parents=True, exist_ok=True)
            mirror = a.receipt_cache / (str(job) + '-receipts.tar.gz')
            if not mirror.exists():
                os.link(receipt, mirror)
            assert hashlib.sha256(mirror.read_bytes()).hexdigest() == expected
            files['receipts_external'] = dict(uri=HOST + ':' + root + '/receipts.tar.gz', bytes=len(data))
            files['receipts_sha256'] = expected
            continue
        name = str(job) + '-' + kind + '.tar.gz.b64'
        (a.out / name).write_bytes(base64.b64encode(data))
        files[kind + '_archive'] = name
        files[kind + '_sha256'] = hashlib.sha256(data).hexdigest()
    index = a.out / 'index.json'
    document = json.loads(index.read_text(encoding='utf-8')) if index.exists() else dict(runs=[])
    assert not any(r['job'] == job for r in document['runs']), 'immutable run already indexed'
    document['runs'].append(dict(job=job, state=fields[1], family=a.family, source_commit=submission['source_commit'],
        remote_root=root, accounting=state, **files))
    index.write_text(json.dumps(document, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(document['runs'][-1]))


if __name__ == '__main__':
    main()
