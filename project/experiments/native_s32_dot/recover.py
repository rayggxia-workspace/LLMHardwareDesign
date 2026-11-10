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


def recover(directory,index_generated=False):
    stage=json.loads((directory/'stage.json').read_text())
    remote=stage['remote']
    assert remote.startswith('/public/home/yuzelu/project-circuit/issue252-native32-')
    script='''import hashlib,io,json,pathlib,sys,tarfile
root=pathlib.Path(sys.argv[1]);files={};inventory={};index_generated=sys.argv[2]=='1'
for p in root.rglob('*'):
 if not p.is_file():continue
 r=p.relative_to(root).as_posix()
 if r.startswith('source/') or '/obj-' in r or r.endswith('.tar.gz'):continue
 if p.suffix in ('.log','.json','.txt','.csv') or p.name in ('source.sha256',):
  if index_generated and p.suffix=='.log' and p.stat().st_size>262144:
   with p.open('rb') as f:
    digest=hashlib.sha256()
    for block in iter(lambda:f.read(1048576),b''):digest.update(block)
    inventory[r]=digest.hexdigest();f.seek(-16384,2);files[r+'.tail']=f.read()
   continue
  raw=p.read_bytes();inventory[r]=hashlib.sha256(raw).hexdigest()
  first_seed=r.startswith('seed-25201/')
  if index_generated and (p.name=='core.txt' or (p.name=='service.txt' and not first_seed)
    or (p.suffix=='.csv' and (not first_seed or p.name not in ('timing-0-0.csv','timing-1-0.csv')))):continue
  files[r]=raw
files['remote-inventory.json']=(json.dumps(inventory,indent=2,sort_keys=True)+'\\n').encode()
with tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz') as a:
 for name,data in sorted(files.items()):
  m=tarfile.TarInfo(name);m.size=len(data);m.mode=0o644;a.addfile(m,io.BytesIO(data))
'''
    raw=subprocess.check_output(['ssh',HOST,shlex.join(['python3','-c',script,remote,str(int(index_generated))])],stdin=subprocess.DEVNULL)
    with tarfile.open(fileobj=io.BytesIO(raw),mode='r:gz') as archive:
        members={m.name:archive.extractfile(m).read() for m in archive if m.isfile()}
    encoded=base64.b64encode(raw);parts=[]
    for i,offset in enumerate(range(0,len(encoded),1024*1024)):
        name='receipts.part-%03d.b64'%i;data=encoded[offset:offset+1024*1024]
        (directory/name).write_bytes(data);parts.append(dict(path=name,sha256=hashlib.sha256(data).hexdigest()))
    result=dict(**stage,receipts_archive_sha256=hashlib.sha256(raw).hexdigest(),parts=parts,index_generated=index_generated,
                members={k:hashlib.sha256(v).hexdigest() for k,v in sorted(members.items())})
    (directory/'recovery.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(job=stage['job'],bytes=len(raw),parts=len(parts),members=len(members))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--index-generated',action='store_true')
    args=p.parse_args();recover(args.run,args.index_generated)
