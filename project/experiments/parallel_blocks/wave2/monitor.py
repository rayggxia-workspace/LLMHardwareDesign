"""Read all three streams, then verify/download their immutable terminal audit."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE=Path(__file__).resolve().parent
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--attempt',required=True)
args=parser.parse_args()
assert re.fullmatch(r'parallel-blocks-wave2-[0-9]+',args.attempt)
remote='/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-7/'+args.attempt
command=['ssh','-o','BatchMode=yes','yuzelu@10.129.166.172']
record=json.loads(subprocess.check_output(command+['python3 - '+remote],input=(HERE/'status.py').read_text(),text=True))
out=HERE.parent/'results'
(out/(args.attempt+'-latest.json')).write_text(json.dumps(record,indent=2)+'\n')
if record['completion_exists'] and record['completion_sha256']:
    raw=subprocess.check_output(command+['cat '+remote+'/completion.json'])
    assert hashlib.sha256(raw).hexdigest()==record['completion_sha256'].split()[0]
    destination=out/(args.attempt+'-completion.json')
    if destination.exists():assert destination.read_bytes()==raw
    else:destination.write_bytes(raw)
    print('Frozen completion SHA verified')
print(record['scheduler']['stdout'])
for name,item in record['tasks'].items():
    print(name,'exit=',str(item['exit_code']).strip(),'stages=',item.get('stages'),
          'quality=',item.get('quality'),'validation=',item.get('validation',{}).get('passed'),
          'RAM cases=',item.get('ram_cases_finished'),'views=',item.get('views_finished'))
    if item['exit_code'] and item['exit_code'].strip()!='0':print(item['log_tail'])
