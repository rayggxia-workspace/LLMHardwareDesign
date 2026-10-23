"""Read only sealed terminal jobs; retain exact bytes of lightweight evidence."""
import argparse
import base64
import hashlib
import gzip
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
       'native-api.log','native-flow-snippets.json','baseline-drc.rpt','baseline-antenna.rpt','native-stack-symbols.txt',
       'debug-tools.json','debug-readelf.log','debug-addr2line.log','debug-gdb.log','connectivity-api.log','proxy-build.log',
       'forest-plan.json','access-plan.json','composite-extract.log','composite-quality.json','composite-native-freeze-audit.json',
       'composite.integration.json','composite.freeze-audit.json','upper-connectivity.json','boundary-proof.json',
       'parent-electrical.rpt','parent-annotation.rpt','composite-antenna.rpt','rc-connectivity.tsv',
       'strict-qualification.log','full-hierarchy-quality.json','full-hierarchy-sta.log','final-pg.log',
       'final-pg/strict-pg.json','h1-qualification-input-sha256.json','signal-pin-layers.tsv','routing-tech-shapes.tsv','boundary.log','readonly-drc.log','readonly-drc-quality.json',
       'readonly-drc-freeze-audit.json','integrated-drc.rpt','annotation-validation.json','annotation-h2.log',
       'h2-unannotated-connectivity.tsv']
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
        compressed=len(raw)>32768 or name.endswith('.rpt')
        target=out/(name+'.gz' if compressed else name)
        target.parent.mkdir(parents=True,exist_ok=True)
        payload=gzip.compress(raw,mtime=0) if compressed else raw
        if target.exists():assert target.read_bytes()==payload,'Changed terminal evidence'
        else:target.write_bytes(payload)
    sacct=subprocess.check_output(['ssh','-o','BatchMode=yes',receipt['host'],
        'sacct -j '+receipt['job_id']+' -X -n -P -o JobID,State,ExitCode,Elapsed,Timelimit'],text=True).strip()
    data.update(job_id=receipt['job_id'],sacct=sacct)
    target=out/'terminal.json'
    if target.exists():
        assert json.loads(target.read_text())['manifest_sha256']==data['manifest_sha256']
    else:target.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(attempt,sacct)
