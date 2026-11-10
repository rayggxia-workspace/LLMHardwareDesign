"""Recover immutable Slurm logs/vectors; never launch numerical work locally."""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import shlex
import subprocess
import tarfile

HOST='yuzelu@10.129.166.172'


def recover(directory):
    stage=json.loads((directory/'stage.json').read_text())
    remote=stage['remote']
    assert remote.startswith('/public/home/yuzelu/project-circuit/issue252-native32-')
    script='''import hashlib,io,json,pathlib,sys,tarfile
root=pathlib.Path(sys.argv[1]);files={}
for p in root.rglob('*'):
 if not p.is_file():continue
 r=p.relative_to(root).as_posix()
 if r.startswith('source/') or '/obj-' in r or r.endswith('.tar.gz'):continue
 if p.suffix in ('.log','.json','.txt') or p.name in ('source.sha256',):files[r]=p.read_bytes()
files['remote-inventory.json']=(json.dumps({k:hashlib.sha256(v).hexdigest() for k,v in sorted(files.items())},indent=2)+'\\n').encode()
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as a:
 for name,data in sorted(files.items()):
  m=tarfile.TarInfo(name);m.size=len(data);m.mode=0o644;a.addfile(m,io.BytesIO(data))
'''
    raw=subprocess.check_output(['ssh',HOST,shlex.join(['python3','-c',script,remote])],stdin=subprocess.DEVNULL)
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
        members={m.name:archive.extractfile(m).read() for m in archive if m.isfile()}
    encoded=base64.b64encode(raw);parts=[]
    for i,offset in enumerate(range(0,len(encoded),1024*1024)):
        name='receipts.part-%03d.b64'%i;data=encoded[offset:offset+1024*1024]
        (directory/name).write_bytes(data);parts.append(dict(path=name,sha256=hashlib.sha256(data).hexdigest()))
    result=dict(**stage,receipts_archive_sha256=hashlib.sha256(raw).hexdigest(),parts=parts,
                members={k:hashlib.sha256(v).hexdigest() for k,v in sorted(members.items())})
    (directory/'recovery.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(job=stage['job'],bytes=len(raw),parts=len(parts),members=len(members))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True)
    recover(p.parse_args().run)
