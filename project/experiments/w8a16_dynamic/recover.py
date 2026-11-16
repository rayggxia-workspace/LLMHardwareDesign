"""Recover small receipts, preserving failures; each Git blob <=1MiB."""
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
CODE='''import hashlib,io,json,pathlib,sys,tarfile
root=pathlib.Path(sys.argv[1]);assert str(root).startswith('/public/home/yuzelu/project-circuit/issue250-dynamic-')
stream=io.BytesIO();large=[]
with tarfile.open(fileobj=stream,mode='w:gz') as tar:
 for p in sorted(root.rglob('*')):
  rel=p.relative_to(root)
  if p.is_file() and 'source' not in rel.parts and not any(v.startswith('obj-') for v in rel.parts) and p.suffix in ('.json','.log','.txt','.sha256','.csv','.sv','.v','.ys','.scl'):
   if p.stat().st_size>=10000000:
    digest=hashlib.sha256()
    with p.open('rb') as src:
     for block in iter(lambda:src.read(1048576),b''):digest.update(block)
    large.append(dict(path=str(p),bytes=p.stat().st_size,sha256=digest.hexdigest(),status='retained on authorized server; indexed, not copied locally'))
   else:tar.add(p,arcname=rel.as_posix(),recursive=False)
 if large:
  data=(json.dumps(large,indent=2)+'\\n').encode();info=tarfile.TarInfo('remote-large-files.json');info.size=len(data);tar.addfile(info,io.BytesIO(data))
sys.stdout.buffer.write(stream.getvalue())
'''


def receipts(run):
    recovery=json.loads((run/'recovery.json').read_text())
    data=b''.join((run/p['path']).read_bytes() for p in recovery['parts'])
    assert all(hashlib.sha256((run/p['path']).read_bytes()).hexdigest()==p['sha256'] for p in recovery['parts'])
    raw=base64.b64decode(data,validate=True)
    assert hashlib.sha256(raw).hexdigest()==recovery['archive_sha256']
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
        result={m.name:archive.extractfile(m).read() for m in archive if m.isfile()}
    assert {k:hashlib.sha256(v).hexdigest() for k,v in result.items()}==recovery['members']
    return recovery,result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);args=p.parse_args()
    stage=json.loads((args.run/'stage.json').read_text())
    assert hashlib.sha256((args.run/'source.tar.gz').read_bytes()).hexdigest()==stage['source_archive_sha256']
    raw=subprocess.check_output(['ssh',HOST,shlex.join(['python3','-c',CODE,stage['remote']])],stdin=subprocess.DEVNULL)
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
        members={m.name:hashlib.sha256(archive.extractfile(m).read()).hexdigest() for m in archive if m.isfile()}
    data=base64.b64encode(raw);(args.run/'receipt-parts').mkdir(exist_ok=False)
    parts=[]
    for offset in range(0,len(data),1048576):
        path=f'receipt-parts/{offset//1048576:03d}.b64';piece=data[offset:offset+1048576]
        (args.run/path).write_bytes(piece)
        parts.append(dict(path=path,bytes=len(piece),sha256=hashlib.sha256(piece).hexdigest()))
    report=dict(stage,archive_sha256=hashlib.sha256(raw).hexdigest(),members=members,parts=parts,
                sacct=subprocess.check_output(['ssh',HOST,shlex.join(['sacct','-j',stage['job'],'--format=JobID,State,ExitCode,Elapsed','--noheader'])],stdin=subprocess.DEVNULL).decode())
    (args.run/'recovery.json').write_text(json.dumps(report,indent=2)+'\n')
    checked,files=receipts(args.run)
    print(json.dumps(dict(job=stage['job'],archive_sha256=checked['archive_sha256'],files=len(files),parts=len(parts))))
