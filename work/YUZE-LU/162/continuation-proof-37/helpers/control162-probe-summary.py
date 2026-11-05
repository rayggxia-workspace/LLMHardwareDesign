import subprocess,shlex,sys
n=int(sys.argv[1]);assert n>=155
q=r'''from pathlib import Path
import json
N=0
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');p=b/('router-fastroute24phase-preflight-172'if N==172 else 'router-fastroute24-preflight-171'if N==171 else 'router-fastroute-preflight-170'if N==170 else 'router-openroad-effort-preflight-157'if N==157 else'router-openroad-preflight-'+str(N))
for f in [p/'receipt.json',p/'openroad-probe.json']:
 if not f.exists():print('Pending',str(f));continue
 d=json.loads(f.read_text());print(str(f),json.dumps({k:v for k,v in d.items()if k in ['passed','stage','whole_system_qualified','congestion_iterations','independent_grid_verification_passed']}))
 if 'cases'in d:print('cases',[(r['case'],r['returncode'],len(r.get('outputs',{})))for r in d['cases']],'negative',d['parser_regression']['negative_cases'])
for folder in p.glob('case-*'):
 f=folder/'grid-proof.json';print(folder.name,'grid',json.loads(f.read_text()).get('checked_edges')if f.exists()else'pending')
 if not f.exists()and(folder/'openroad.log').exists():print((folder/'openroad.log').read_text()[-1200:])
'''.replace('N=0','N='+str(n))
print(subprocess.check_output(['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
