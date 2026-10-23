"""Read only sealed terminal jobs; retain exact bytes of lightweight evidence."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import shlex
import subprocess

HERE=Path(__file__).resolve().parent
p=argparse.ArgumentParser()
p.add_argument('attempts',nargs='+')
a=p.parse_args()
names=['exit-code.txt','finished.txt','allocation.txt','image.sha256','tools.sha256',
       'spec.json','input-sha256.json','inputs.json','partition.json','budget.log',
       'electrical-budget.rpt','interface-nets.rpt','macro-nets.txt','partition.log',
       'route.log','restricted-drc.rpt','freeze-audit.json','inventory-summary.json',
       'native-api.log','native-flow-snippets.json','baseline-drc.rpt','baseline-antenna.rpt']
for attempt in a.attempts:
    receipt=json.loads((HERE/'results'/(attempt+'-submission.json')).read_text())
    remote=receipt['spec']['remote']
    program='''import base64,hashlib,json
from pathlib import Path
r=Path(REMOTE)
if not (r/'output.sha256').exists():
 print(json.dumps(dict(terminal=False)))
else:
 data=(r/'output.sha256').read_bytes()
 manifest={n[2:]:h for h,n in (s.split(None,1) for s in data.decode().splitlines())}
 files={}
 for name in NAMES:
  path=r/name
  if path.is_file():
   raw=path.read_bytes(); h=hashlib.sha256(raw).hexdigest()
   assert manifest[name]==h,name
   assert len(raw)<12000000,name
   files[name]=dict(sha256=h,base64=base64.b64encode(raw).decode())
 print(json.dumps(dict(terminal=True,manifest_sha256=hashlib.sha256(data).hexdigest(),manifest=manifest,files=files)))
'''.replace('REMOTE',repr(remote)).replace('NAMES',repr(names))
    payload=subprocess.check_output(['ssh','-o','BatchMode=yes',receipt['host'],'python3 -c '+shlex.quote(program)],text=True)
    data=json.loads(payload)
    if not data['terminal']:
        print(attempt,'not sealed');continue
    out=HERE/'results'/attempt
    out.mkdir(exist_ok=True)
    for name,item in data.pop('files').items():
        raw=base64.b64decode(item['base64'])
        assert hashlib.sha256(raw).hexdigest()==item['sha256']
        target=out/name
        if target.exists():assert target.read_bytes()==raw,'Changed terminal evidence'
        else:target.write_bytes(raw)
    sacct=subprocess.check_output(['ssh','-o','BatchMode=yes',receipt['host'],
        'sacct -j '+receipt['job_id']+' -X -n -P -o JobID,State,ExitCode,Elapsed,Timelimit'],text=True).strip()
    data.update(job_id=receipt['job_id'],sacct=sacct)
    target=out/'terminal.json'
    if target.exists():
        assert json.loads(target.read_text())['manifest_sha256']==data['manifest_sha256']
    else:target.write_text(json.dumps(data,indent=2)+'\n')
    print(attempt,sacct)
