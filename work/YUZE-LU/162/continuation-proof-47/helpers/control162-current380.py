import subprocess,shlex
q=r'''from pathlib import Path
import json,time,subprocess
b=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-162');r=b/'r256-composition-359'
def tail(p,n=3):
 if not p.exists():return []
 with p.open('rb')as f:f.seek(max(0,p.stat().st_size-3500));return f.read().decode(errors='replace').splitlines()[-n:]
for seed in [3730,3731,3732,3733,3734,3740,3741,3750,3751]:
 p=r/'upper-candidates'/str(seed)/'route';rc=p/'receipt.json';d=json.loads(rc.read_text())if rc.exists()else{}
 print('route',seed,{k:d[k]for k in ['passed','error','stage']if k in d})
 for f in list(p.glob('trial-0/router.log'))+list(p.glob('openroad-search/case-0/openroad.log')):print(f.name,tail(f,2))
for folder in ['dynamic-05/node2','dynamic-02/node3','dynamic-05/node4','dynamic-03/node5','dynamic-02/node6','dynamic-04/node25','dynamic-07/node7','dynamic-06/node26']:
 p=b/folder/'queue-state.json';d=json.loads(p.read_text())if p.exists()else{};print(folder,'active',d.get('active'),'waiting',len(d.get('waiting_for_complete_receipts',[])))
 for f in(b/folder).glob('*sready384*log'):print(f.name,[v[-700:]for v in tail(f,3)])
p=r/'function';print('function_build', [v[-240:]for v in tail(p/'build.log',1)]);print('func_results',[(f.name,f.stat().st_size)for f in p.glob('*')if f.is_file()and f.suffix=='.json'])
for p in [b/'r256-directional-regression-384',r/'upper-candidates/3840/route',r/'upper-candidates/3841/route']:
 f=p/'receipt.json';d=json.loads(f.read_text())if f.exists()else{};print('new',str(p.relative_to(b)),{k:d[k]for k in ['passed','stage','error']if k in d})
print(subprocess.check_output(['squeue','-h','-j','95341,95098,95391,95155,95101,95204,96297,96222','-o','%i %T %N']).decode())
'''
print(subprocess.check_output(['ssh','-o','ConnectTimeout=10','yuzelu@10.129.166.172','python3 -c '+shlex.quote(q)],timeout=45).decode())
