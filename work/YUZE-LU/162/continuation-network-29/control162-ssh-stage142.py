"""Bounded SSH handshake diagnosis; print protocol stages only."""
import subprocess,json,sys
from datetime import datetime,timezone
from pathlib import Path

client=r'C:\Program Files\Git\usr\bin\ssh.exe'if '--git-client'in sys.argv else 'ssh'
options=[]
if '--git-client'in sys.argv:
    options=['-o','UserKnownHostsFile=C:/Users/wine10/.ssh/known_hosts']
    # Reuse the identity selected by the existing Windows `ssh -G` config.
    for filename in ['id_rsa_windows']:
        identity=Path('C:/Users/wine10/.ssh')/filename
        if identity.exists():options+=['-i',identity.as_posix()]
try:
    r=subprocess.run([client]+options+['-v','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=30',
                      '-o','ServerAliveInterval=30','-o','ServerAliveCountMax=1',
                      'yuzelu@10.129.166.172','hostname'],capture_output=True,text=True,timeout=55)
    stages=[line for line in r.stderr.splitlines()if any(s in line.lower()for s in (
        'connection established','local version','remote protocol','kex_exchange',
        'kex:','connection reset','connection closed','timed out','authenticat',
        'exit status','sending command','verification failed','permission denied',
        'host key verification','no matching','known_hosts','host identification',
        'bad owner','bad permissions','unable to negotiate'))]
    d=dict(time=datetime.now(timezone.utc).isoformat(),returncode=r.returncode,protocol_stages=stages,stdout=r.stdout,error_tail=r.stderr.splitlines()[-4:]if r.returncode else [])
except subprocess.TimeoutExpired:
    d=dict(time=datetime.now(timezone.utc).isoformat(),timeout_seconds=55)
d['client']=client
line=json.dumps(d,ensure_ascii=False)
with Path(__file__).with_suffix('.jsonl').open('a',encoding='utf-8')as f:f.write(line+'\n')
print(line)
