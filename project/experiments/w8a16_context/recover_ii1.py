"""Recover only bounded unit receipts from this subtask's new remote directory."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import shlex
import subprocess
import tarfile

HOST = 'yuzelu@10.129.166.172'
CODE = '''import io,pathlib,sys,tarfile
root=pathlib.Path(sys.argv[1]); stream=io.BytesIO()
assert str(root).startswith('/public/home/yuzelu/project-circuit/issue250-context-20261111-10')
with tarfile.open(fileobj=stream,mode='w:gz') as tar:
 for path in sorted(root.rglob('*')):
  rel=path.relative_to(root)
  if path.is_file() and 'source' not in rel.parts and not any(p.startswith('obj') for p in rel.parts) and path.suffix in ('.json','.log','.txt','.sha256','.csv','.hex','.vh'):
   assert path.stat().st_size<8000000
   tar.add(path,arcname=rel.as_posix(),recursive=False)
sys.stdout.buffer.write(stream.getvalue())
'''


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--run', type=Path, required=True)
    args = p.parse_args()
    record = json.loads((args.run / 'submission.json').read_text())
    assert hashlib.sha256((args.run / 'source.tar.gz').read_bytes()).hexdigest() == record['package_sha256']
    data = subprocess.check_output(['ssh', HOST, shlex.join(['python3', '-c', CODE, record['remote_root']])], stdin=subprocess.DEVNULL)
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as archive:
        members = {m.name: hashlib.sha256(archive.extractfile(m).read()).hexdigest() for m in archive if m.isfile()}
    (args.run / 'receipts.tar.gz.b64').write_bytes(base64.b64encode(data))
    record['receipts_sha256'] = hashlib.sha256(data).hexdigest()
    record['members'] = members
    record['sacct'] = subprocess.check_output(['ssh', HOST, shlex.join(['sacct', '-j', record['submit'].split()[-1], '--format=JobID,State,ExitCode,Elapsed', '--noheader'])], stdin=subprocess.DEVNULL).decode()
    (args.run / 'recovery.json').write_text(json.dumps(record, indent=2)+'\n')
    print(json.dumps(dict(job=record['submit'].split()[-1], files=len(members), sha256=record['receipts_sha256'])))
