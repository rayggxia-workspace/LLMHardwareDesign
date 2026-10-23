"""Network-only bounded-memory relay to own server, no local weight files.

Public source files are pinned by ModelScope file commit and SHA, with official
HF LFS SHA/Git blob checks. All model loading and experiment compute stays Slurm.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shlex
import subprocess
import time
import urllib.request
from urllib.parse import urlparse

SSH=['C:/Windows/System32/OpenSSH/ssh.exe','-i','C:/Users/23123/.ssh/id_ed25519_liangruizhi_lab_20261020',
     '-o','IdentitiesOnly=yes','-o','BatchMode=yes','yuzelu@10.129.166.172']
PYTHON='/public/home/yuzelu/python-3.12/bin/python3.12'
RECEIVER='/public/home/yuzelu/RuizhiLiang/issue61-server-models-20261023/phase3/receive_stream.py'


def one(record):
    if urlparse(record['url']).hostname!='www.modelscope.cn':raise ValueError('unexpected source host')
    args=[PYTHON,'-B',RECEIVER,'--model',record['model'],'--file',record['name'],'--size',str(record['bytes']),'--sha256',record['sha256']]
    if record.get('official_git_blob'):args+=['--git-blob',record['official_git_blob']]
    failures=[];start=time.monotonic()
    for attempt in range(3):
        try:
            status=subprocess.run(SSH+[shlex.join(args+['--status'])],capture_output=True,check=True,timeout=60)
            state=json.loads(status.stdout)
            if state['status']=='VERIFIED':return {**record,'server':state,'seconds':time.monotonic()-start,'failures':failures,'reused':True}
            offset=state['offset'];headers={'User-Agent':'LLMHardwareDesign-verified-model-relay','Accept-Encoding':'identity'}
            if offset:headers['Range']='bytes='+str(offset)+'-'
            with urllib.request.urlopen(urllib.request.Request(record['url'],headers=headers),timeout=60)as response:
                if offset and (response.status!=206 or not response.headers.get('Content-Range','').startswith('bytes '+str(offset)+'-')):raise ValueError('resume not honored')
                proc=subprocess.Popen(SSH+[shlex.join(args+['--offset',str(offset)])],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                current=offset;last=time.monotonic()
                try:
                    while True:
                        block=response.read(1<<20)
                        if not block:break
                        proc.stdin.write(block);current+=len(block)
                        if time.monotonic()-last>15:
                            print(json.dumps({'model':record['model'],'file':record['name'],'bytes':current,'total':record['bytes'],'seconds':time.monotonic()-start}),flush=True);last=time.monotonic()
                finally:proc.stdin.close();proc.stdin=None
                stdout,stderr=proc.communicate(timeout=120)
                if proc.returncode:raise RuntimeError(stderr.decode(errors='replace'))
                result=json.loads(stdout)
            print(json.dumps({'model':record['model'],'file':record['name'],'verified':True,'seconds':time.monotonic()-start}),flush=True)
            return {**record,'server':result,'seconds':time.monotonic()-start,'failures':failures,'reused':False}
        except Exception as exc:
            failures.append({'attempt':attempt+1,'type':type(exc).__name__,'error':str(exc)})
            print(json.dumps({'model':record['model'],'file':record['name'],'failed':failures[-1]}),flush=True)
    raise RuntimeError(json.dumps({'file':record['name'],'failures':failures}))


def main():
    p=argparse.ArgumentParser();p.add_argument('--plan',required=True,type=Path);p.add_argument('--model',choices=['phi','gemma'],required=True)
    p.add_argument('--out',required=True,type=Path);p.add_argument('--small-only',action='store_true');a=p.parse_args()
    if a.out.exists():raise ValueError('refuse output overwrite')
    plan=json.loads(a.plan.read_text());records=[r for r in plan['files'] if r['model']==a.model and (not a.small_only or not r['name'].endswith('.safetensors'))]
    small=[r for r in records if not r['name'].endswith('.safetensors')];large=[r for r in records if r['name'].endswith('.safetensors')]
    results=[]
    for r in small:results.append(one(r))
    with ThreadPoolExecutor(max_workers=2)as pool:results.extend(pool.map(one,large))
    a.out.write_text(json.dumps({'status':'PASS','model':a.model,'files':results,'local_weight_files':False},indent=2)+'\n',newline='\n')


if __name__=='__main__':main()
