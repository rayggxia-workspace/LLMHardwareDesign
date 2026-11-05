from pathlib import Path
import subprocess,json,datetime
h=Path(__file__).parent;request=json.loads((h/'control162-online630-pr-request.json').read_text(encoding='utf-8'));r=json.loads(subprocess.check_output(['gh','api','repos/rayggxia-workspace/LLMHardwareDesign/pulls/163']))
assert r['body']==request['body']and r['draft']and r['state']=='open'and not r['merged']and r['head']['sha']=='1b3a4cbe28fecc30e726b836930024debbd1936a'
d=dict(passed=True,time=datetime.datetime.now().astimezone().isoformat(),body_readback_exact=True,head=r['head']['sha'],draft=r['draft'],state=r['state'],merged=r['merged'],body=r['body']);(h/'control162-online630-pr-verified.json').write_bytes((json.dumps(d,indent=2)+'\n').encode());print(json.dumps({k:v for k,v in d.items()if k!='body'}))
