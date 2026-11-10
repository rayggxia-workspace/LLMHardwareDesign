"""Recover immutable task-owned receipts; verify every embedded byte locally.

No simulator or EDA runs on the login node. This packages completed Slurm output
and generated source only. Large build objects/traces stay remote; input SHA and
reproduction sources are retained. Existing evidence directories are never reused.
"""
import argparse
import base64
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile

from prepare import REPO

REMOTE = r'''
import gzip,hashlib,io,json,subprocess,tarfile
from pathlib import Path
r=Path(ROOT)
jobs=JOBS
account=subprocess.check_output(['sacct','-j',','.join(jobs),'-X','-P','-n',
 '--format=JobIDRaw,State,ExitCode,ElapsedRaw,AllocCPUS,NodeList'],universal_newlines=True)
rows=[line.split('|') for line in account.strip().splitlines()]
assert {x[0] for x in rows}==set(jobs),account
assert all(x[1] in ('COMPLETED','FAILED') for x in rows),account
selected=[]
for p in r.iterdir():
 if p.is_file() and (p.suffix in ('.log','.txt','.sha256') or p.name=='job.sh'):selected.append(p)
for folder in ('results','quality'):
 for p in (r/folder).rglob('*'):
  if p.is_file() and not any(x.startswith('obj') for x in p.relative_to(r).parts):
   if p.suffix in ('.json','.log') or p.name.startswith('plan-') and p.suffix=='.txt':selected.append(p)
for p in (r/'restored/candidate').rglob('*'):
 if p.is_file() and p.suffix in ('.cpp','.h','.hpp','.inc'):selected.append(p)
for p in (r/'source/project/experiments/stream_quant_synthesis').iterdir():
 if p.is_file():selected.append(p)
payload={p.relative_to(r).as_posix():p.read_bytes() for p in sorted(set(selected))}
payload['collection-sacct.txt']=account.encode()
index=dict(root=str(r),source_commit=(r/'source-commit.txt').read_text().strip(),jobs=rows,
 files={n:dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest()) for n,b in sorted(payload.items())})
index_bytes=(json.dumps(index,indent=2)+'\n').encode()
payload['evidence-index.json']=index_bytes
archive=r/'evidence-v1.tar.gz'
assert not archive.exists(),str(archive)
with archive.open('xb') as disk:
 with gzip.GzipFile(fileobj=disk,mode='wb',mtime=0) as zipped:
  with tarfile.open(fileobj=zipped,mode='w') as tar:
   for n,b in sorted(payload.items()):
    info=tarfile.TarInfo(n);info.size=len(b);info.mode=0o644;tar.addfile(info,io.BytesIO(b))
print(json.dumps(dict(root=str(r),archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
 archive_bytes=archive.stat().st_size,index=index)))
'''


def verify(folder):
    receipt=json.loads((folder/'receipt.json').read_text())
    raw=base64.b64decode((folder/'evidence.tar.gz.b64').read_bytes(),validate=True)
    assert hashlib.sha256(raw).hexdigest()==receipt['archive_sha256']
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as tar:
        members=tar.getmembers();assert len(members)==len({m.name for m in members})
        embedded=json.loads(tar.extractfile('evidence-index.json').read())
        assert embedded==receipt['index']
        assert {m.name for m in members}==set(embedded['files'])|{'evidence-index.json'}
        for name,expected in embedded['files'].items():
            data=tar.extractfile(name).read()
            assert len(data)==expected['bytes'] and hashlib.sha256(data).hexdigest()==expected['sha256'],name
    return len(embedded['files'])


def collect(tag,jobs,destination):
    if not tag.isdigit() or not all(j.isdigit() for j in jobs):raise ValueError('numeric run/jobs only')
    target=destination/('run'+tag);target.mkdir(parents=True,exist_ok=False)
    root='/public/home/yuzelu/project-circuit/issue248-stream-quant-20261110-'+tag
    script=REMOTE.replace('ROOT',repr(root)).replace('JOBS',repr(jobs))
    text=subprocess.check_output(['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172','python3 -'],input=script,text=True)
    receipt=json.loads(text)
    raw=target/'evidence.tar.gz'
    subprocess.run(['scp','-q','yuzelu@10.129.166.172:'+root+'/evidence-v1.tar.gz',str(raw)],check=True)
    (target/'evidence.tar.gz.b64').write_bytes(base64.b64encode(raw.read_bytes()))
    raw.unlink()  # Only this exact newly downloaded task artifact; no recursive cleanup.
    (target/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf8')
    return dict(run=tag,files_verified=verify(target),archive_bytes=receipt['archive_bytes'])


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('tag');p.add_argument('--jobs',nargs='+',required=True)
    p.add_argument('--out',type=Path,default=REPO/'work/YUZE-LU/248')
    a=p.parse_args();print(json.dumps(collect(a.tag,a.jobs,a.out)))
