"""Recover bounded reports/logs from this subtask's immutable run root."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import shlex
import subprocess
import tarfile
from datetime import datetime, timezone

HOST = 'yuzelu@10.129.166.172'
PREFIX = '/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-250-native-service-'
CODE = r'''
import io,pathlib,sys,tarfile
root=pathlib.Path(sys.argv[1]); stream=io.BytesIO()
assert str(root).startswith('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-250-native-service-')
with tarfile.open(fileobj=stream,mode='w:gz') as tar:
 for path in sorted(root.rglob('*')):
  rel=path.relative_to(root)
  if path.is_file() and 'source' not in rel.parts and path.suffix in ('.json','.log','.txt','.sha256','.csv'):
   assert path.stat().st_size<8000000,(str(path),path.stat().st_size)
   tar.add(path,arcname=rel.as_posix(),recursive=False)
sys.stdout.buffer.write(stream.getvalue())
'''


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    record = json.loads((args.run / 'stage.json').read_text())
    assert record['remote'].startswith(PREFIX)
    data = subprocess.check_output(['ssh', HOST, shlex.join(['python3', '-c', CODE, record['remote']])], stdin=subprocess.DEVNULL)
    with tarfile.open(fileobj=io.BytesIO(data), mode='r:gz') as tar:
        members = {}
        for member in tar:
            assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
            members[member.name] = hashlib.sha256(tar.extractfile(member).read()).hexdigest()
    (args.run / 'receipts.tar.gz.b64').write_bytes(base64.encodebytes(data))
    record.update(receipts_archive_sha256=hashlib.sha256(data).hexdigest(), members=members)
    record['recovered_at'] = datetime.now(timezone.utc).isoformat()
    record['sacct'] = subprocess.check_output([
        'ssh', HOST, shlex.join(['sacct', '-j', str(record['job']), '--format=JobID,State,ExitCode,Elapsed', '--noheader'])],
        stdin=subprocess.DEVNULL).decode().strip()
    (args.run / 'recovery.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(dict(job=record['job'], files=len(members), archive_sha256=record['receipts_archive_sha256'])))
