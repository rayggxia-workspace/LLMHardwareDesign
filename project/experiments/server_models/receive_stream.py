"""Fixed-root server receiver; verified EOF publishes a model file atomically."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT=Path('/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/models')
DIRS={'phi':'phi4mini-cfbefacb','gemma':'gemma3-4b-093f9f38'}


def check(path,size,sha,blob):
    h=hashlib.sha256();g=hashlib.sha1(('blob '+str(path.stat().st_size)+'\0').encode())
    with path.open('rb')as f:
        for b in iter(lambda:f.read(8<<20),b''):h.update(b);g.update(b)
    if path.stat().st_size!=size or h.hexdigest()!=sha or (blob and g.hexdigest()!=blob):raise ValueError('server full-file hash/size mismatch')
    return {'bytes':size,'sha256':h.hexdigest(),'git_blob':g.hexdigest()}


def main():
    p=argparse.ArgumentParser();p.add_argument('--model',choices=list(DIRS),required=True);p.add_argument('--file',required=True)
    p.add_argument('--size',type=int,required=True);p.add_argument('--sha256',required=True);p.add_argument('--git-blob')
    p.add_argument('--offset',type=int,default=0);p.add_argument('--status',action='store_true');a=p.parse_args()
    if not re.fullmatch(r'[A-Za-z0-9_.-]+',a.file) or a.file.startswith('.') or a.size<=0:raise ValueError('file domain')
    folder=ROOT/DIRS[a.model];folder.mkdir(parents=True,exist_ok=True);dest=folder/a.file;part=folder/(a.file+'.relay-part')
    if dest.exists():
        print(json.dumps({'status':'VERIFIED','file':str(dest),**check(dest,a.size,a.sha256,a.git_blob)}));return
    offset=part.stat().st_size if part.exists() else 0
    if a.status:
        print(json.dumps({'status':'PARTIAL','offset':offset,'expected_bytes':a.size}));return
    if a.offset!=offset or offset>a.size:raise ValueError('offset changed')
    with part.open('ab')as f:
        while True:
            raw=sys.stdin.buffer.read(1<<20)
            if not raw:break
            if f.tell()+len(raw)>a.size:raise ValueError('stream exceeds expected size')
            f.write(raw)
    result=check(part,a.size,a.sha256,a.git_blob)
    part.rename(dest)
    print(json.dumps({'status':'VERIFIED','file':str(dest),**result}))


if __name__=='__main__':main()
