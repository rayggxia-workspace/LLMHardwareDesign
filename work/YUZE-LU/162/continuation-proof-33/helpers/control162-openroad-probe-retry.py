"""Append a new source/output probe in the now-free own slot; never overwrite."""
import subprocess,shlex,sys
n=int(sys.argv[1]);assert n>=147
q=r'''from pathlib import Path
import json,hashlib,subprocess
N=0
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');source=b/('source-'+str(N));assert(source/'source-manifest.json').is_file()
queue=b/'dynamic-05/node2';d=json.loads((queue/'queue-state.json').read_text());assert len(d['active'])<=3
details=subprocess.check_output(['scontrol','show','job','95341','-o'],universal_newlines=True);assert 'UserId=yuzelu(10011)'in details and 'JobName=yzl-ctl162-'in details and 'NodeList=node2 'in details
old=json.loads((queue/'pending/00-r-sready146-openroad-preflight.json').read_text());out=b/('router-openroad-preflight-'+str(N));p=queue/'pending'/('00-r-sready'+str(N)+'-openroad-preflight.json');assert not out.exists()and not p.exists()
spec=dict(old,source_root=str(source),args=[str(out)if x==str(b/'router-openroad-preflight-01')else x for x in old['args']]);tmp=p.with_suffix('.tmp');tmp.write_text(json.dumps(spec));tmp.rename(p)
print(json.dumps(dict(spec=str(p),sha256=hashlib.sha256(p.read_bytes()).hexdigest(),output=str(out))))
'''.replace('N=0','N='+str(n))
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
