"""Stage one immutable run and call the existing issue-wide submit authority."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess

HOST = 'yuzelu@10.129.166.172'
BASE = PurePosixPath('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-121')


def remote(code):
    result = subprocess.run(['ssh', '-o', 'BatchMode=yes', '-o', 'ConnectTimeout=10',
                             HOST, 'python3 -'], input=code, text=True,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    assert result.returncode == 0, result.stdout
    return result.stdout


def launch(folder, run_id):
    assert re.fullmatch(r'block-v1-\d{8}-\d{3}', run_id)
    names = ['source.tar', 'manifest.json', 'node-queue.json']
    assert all((folder / name).is_file() for name in names)
    run = str(BASE / run_id)
    digest = hashlib.sha256((folder / 'source.tar').read_bytes()).hexdigest()
    print(remote('from pathlib import Path\nr=Path(' + repr(run) + ')\n'
                 'assert not r.exists(), "Immutable run already exists"\nr.mkdir()\nprint(r)\n'), flush=True)
    subprocess.run(['scp', '-q', *[str(folder / n) for n in names], HOST + ':' + run + '/'], check=True)
    code = '''import hashlib,json,subprocess,tarfile
from pathlib import Path
r=Path(RUN)
assert hashlib.sha256((r/'source.tar').read_bytes()).hexdigest()==DIGEST
src=r/'src';src.mkdir()
with tarfile.open(str(r/'source.tar')) as tar:
 for m in tar.getmembers():
  target=src/m.name
  assert m.isfile() and src.resolve() in target.resolve().parents
  target.parent.mkdir(parents=True,exist_ok=True)
  target.write_bytes(tar.extractfile(m).read())
d=json.loads((src/'bundle-manifest.json').read_text())
for item in d['files']:
 assert hashlib.sha256((src/item['path']).read_bytes()).hexdigest()==item['sha256']
print('VERIFIED',d['source_commit'],len(d['files']))
subprocess.check_call(['python3',str(src/'project/experiments/block_v1/dispatch.py'),str(r/'manifest.json'),'--submit'])
'''.replace('RUN', repr(run)).replace('DIGEST', repr(digest))
    result = remote(code)
    (folder / 'submission.txt').write_text(result, encoding='utf-8')
    print(result)


if __name__ == '__main__':
    p = argparse.ArgumentParser(__doc__)
    p.add_argument('folder', type=Path)
    p.add_argument('--run-id', required=True)
    a = p.parse_args()
    launch(a.folder, a.run_id)
