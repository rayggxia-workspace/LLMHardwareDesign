"""Collect completed owned receipts without running simulation on a login host."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shlex
import subprocess
import tarfile

HOST = 'yuzelu@10.129.166.172'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--root', required=True)
    p.add_argument('--dest', required=True, type=Path)
    p.add_argument('--job', required=True, type=int)
    a = p.parse_args()
    assert re.fullmatch(r'/public/home/yuzelu/project-circuit/issue250-weight-20261111-[0-9]+', a.root)
    a.dest.mkdir(exist_ok=True, parents=True)
    script = '''import hashlib,json,pathlib,tarfile
root=pathlib.Path(ROOT)
paths=[]
for path in root.rglob('*'):
 if not path.is_file() or 'obj' in path.parts or path.name in ('receipts.tar.gz','receipts-manifest.json','source.tar.gz'):continue
 paths.append(path)
manifest={str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}
(root/'receipts-manifest.json').write_text(json.dumps(manifest,indent=2)+'\\n')
with tarfile.open(root/'receipts.tar.gz','w:gz') as archive:
 for path in paths+[root/'receipts-manifest.json']:archive.add(path,arcname=str(path.relative_to(root)))
print(json.dumps(dict(files=len(paths),SHA256=hashlib.sha256((root/'receipts.tar.gz').read_bytes()).hexdigest())))
'''.replace('ROOT', repr(a.root))
    metadata = subprocess.check_output(['ssh', '-o', 'BatchMode=yes', HOST, 'python3 -c ' + shlex.quote(script)]).decode().strip()
    archive = a.dest / 'receipts.tar.gz'
    subprocess.run(['scp', '-q', HOST + ':' + a.root + '/receipts.tar.gz', str(archive)], check=True)
    record = json.loads(metadata)
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == record['SHA256']
    extracted = a.dest / 'receipts'
    extracted.mkdir(exist_ok=False)
    with tarfile.open(archive, 'r:gz') as package:
        for item in package.getmembers():
            assert item.isfile() and not Path(item.name).is_absolute() and '..' not in Path(item.name).parts
        package.extractall(extracted, filter='data')
    manifest = json.loads((extracted / 'receipts-manifest.json').read_text())
    for name, sha in manifest.items():
        assert hashlib.sha256((extracted / name).read_bytes()).hexdigest() == sha
    accounting = subprocess.check_output(['ssh', '-o', 'BatchMode=yes', HOST,
        f'sacct -j {a.job} --format=JobID,JobName,State,Elapsed,ExitCode,AllocCPUS,NodeList -P']).decode()
    (a.dest / 'accounting.txt').write_text(accounting)
    record.update(remote_root=a.root, job=a.job, files_checked=len(manifest))
    (a.dest / 'collection.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record))


if __name__ == '__main__':
    main()
