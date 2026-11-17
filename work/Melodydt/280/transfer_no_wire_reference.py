"""Stream only accepted G32/switch power inputs between authorized servers.

No waveform or implementation archive is stored on the client. Authentication
uses the existing old-server key and an in-memory new-server password prompt.
"""
import getpass
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'tmp/issue280-python'))
import paramiko

workspace=Path(__file__).resolve().parents[3]
old=paramiko.SSHClient();old.load_host_keys(str(workspace/'tmp/energy-054-ddr-host.pub'))
old.set_missing_host_key_policy(paramiko.RejectPolicy())
old.connect('10.129.166.172',username='yuzelu',look_for_keys=False,allow_agent=False,
    key_filename='C:/Users/Administrator/.ssh/id_ed25519_server_ops_20261030',timeout=20,auth_timeout=30)
new=paramiko.SSHClient();new.load_host_keys(str(workspace/'tmp/energy-server-known-hosts'))
new.set_missing_host_key_policy(paramiko.RejectPolicy())
new.connect('36.103.203.5',username='t6s011227@BSCC-T6',password=getpass.getpass('BSCC password: '),
    look_for_keys=False,allow_agent=False,timeout=20,auth_timeout=30)
source=old.open_sftp();target=new.open_sftp()
base='/public/home/yuzelu'
dest='/public3/home/t6s011227/LLMHardware/zenanyan/issue-280-bscc-t6-01/no-wire-legacy-power-01'
made=set();transferred={}
def mkdir(path):
    if path in made:return
    try:target.stat(path)
    except FileNotFoundError:
        mkdir(path.rsplit('/',1)[0]);target.mkdir(path)
    made.add(path)
def read(path):
    with source.open(path) as f:return f.read()
def write(path,data):
    mkdir(path.rsplit('/',1)[0])
    with target.open(path+'.part','wb') as f:f.write(data)
    target.posix_rename(path+'.part',path)
def transfer(path):
    if not path.startswith(base+'/') or '..' in Path(path).parts:
        raise ValueError('source outside authorized project storage')
    if path in transferred:return transferred[path]
    destination=dest+'/files/'+path[len(base)+1:]
    mkdir(destination.rsplit('/',1)[0]);h=sha256()
    with target.open(destination+'.part','wb') as f:
        f.set_pipelined(True)
        class Sink:
            def write(self,data):h.update(data);return f.write(data)
        size=source.getfo(path,Sink(),prefetch=True,max_concurrent_prefetch_requests=24)
    target.posix_rename(destination+'.part',destination)
    row={'source':path,'destination':destination,'bytes':size,'sha256':h.hexdigest()}
    transferred[path]=row
    print(json.dumps({'transferred_bytes':size,'source':path}),flush=True)
    return row

groot=base+'/Melodydt/runs/issue-280/c380-g32-power-300-03/result-117749'
sroot=base+'/Melodydt/runs/issue-280/c639-switch-power-300-02/result-117841'
summary_raw=read(groot+'/summary.json');summary=json.loads(summary_raw)
write(dest+'/g32-source-summary.json',summary_raw)
cases={}
for family,labels in [('g32',['mode-%d-%s'%(m,p) for m in (0,1) for p in ('down','gate-up','g32-active')]),
                      ('switch',['mode-%d-%s'%(m,p) for m in (0,1) for p in ('down','gate-up')])]:
    for label in labels:
        path=(groot+'/g32/'+label) if family=='g32' else (sroot+'/'+label+'/power')
        script=read(path+'/power.tcl').decode()
        if family=='g32':
            receipt=summary['g32/'+label]
            receipt['source_summary_sha256']=sha256(summary_raw).hexdigest()
        else:
            receipt=json.loads(read(path+'/receipt.json'))
        refs=re.findall(r'(?m)^read_(?:db|sdc)\s+\{([^}]+)\}',script)
        refs+=re.findall(r'(?m)^read_vcd.*?\{([^}]+\.vcd)\}',script)
        inputs={}
        for name in refs:
            row=transfer(name)
            recorded=receipt.get('input_sha256',{}).get(name)
            if recorded is not None and recorded!=row['sha256']:
                raise ValueError('accepted source changed: '+name)
            script=script.replace('{'+name+'}','{'+row['destination']+'}')
            inputs[row['destination']]=row['sha256']
        receipt['input_sha256']=inputs
        receipt['source_case']=path
        name=family+'-'+label
        write(dest+'/cases/'+name+'/power.tcl',script.encode())
        write(dest+'/cases/'+name+'/receipt.json',(json.dumps(receipt,indent=2)+'\n').encode())
        cases[name]=path
manifest={'cases':cases,'files':list(transferred.values()),'g32_summary_sha256':sha256(summary_raw).hexdigest()}
write(dest+'/transfer.json',(json.dumps(manifest,indent=2)+'\n').encode())
print('LEGACY_POWER_INPUTS_TRANSFERRED',len(cases),len(transferred),flush=True)
source.close();target.close();old.close();new.close()
