"""One bounded, read-only selected-function/halo/route snapshot."""
import subprocess
import shlex
import json
from pathlib import Path
from datetime import datetime, timezone

query = r'''from pathlib import Path
import json,time
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');c=b/'s-ready-composition-01/1391'
for item in ['final-composition','halo-cap-candidates/1470','halo-cap-candidates/1471','halo-cap-candidates/1472','halo-native-residual-01','halo-native-pin-load-01']:
 p=c/item;r=p/'receipt.json'
 if r.exists():
  try:d=json.loads(r.read_text());print(item,json.dumps(d))
  except ValueError:print(item,'incomplete receipt')
 else:print(item,'pending')
for item,name in [('halo-native-residual-01','native-cap-residual.json'),('halo-native-pin-load-01','native-pin-load.json')]:
 p=c/item/name
 if p.exists():
  d=json.loads(p.read_text())
  for row in d.get('placements',[]):print(item,Path(row['placement']).name,'violations',row['violations'])
for n in [1410,1412,1430,1432,1433,1440,1442,1444,1445,1446,1448,1449,1450,1451,1452,1453,1454,1460,1461,1462,1480,1481,1482]:
 p=c/'upper-candidates'/str(n);r=p/'route/receipt.json'
 if r.exists():print('route',n,r.read_text())
 else:
  logs=sorted((p/'route/trial-0').glob('*.log'))
  for log in logs:
   with log.open('rb')as f:f.seek(max(0,log.stat().st_size-350));print('route',n,log.name,f.read().decode(errors='replace'))
'''
stamp=datetime.now(timezone.utc).isoformat()
try:
    r=subprocess.run(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=8',
                      '-o','ServerAliveInterval=8','-o','ServerAliveCountMax=1',
                      'yuzelu@10.129.166.172','python3 -c '+shlex.quote(query)],
                     text=True,capture_output=True,timeout=30)
    event=dict(time=stamp,returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)
except subprocess.TimeoutExpired:
    event=dict(time=stamp,timeout_seconds=30,scope='Only this local read-only SSH query was terminated; no remote Slurm action.')
line=json.dumps(event,ensure_ascii=False)
with Path(__file__).with_suffix('.jsonl').open('a',encoding='utf-8')as stream:
    stream.write(line+'\n')
print(line)
