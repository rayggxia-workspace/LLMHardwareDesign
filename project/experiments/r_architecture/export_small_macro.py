"""Generate actual ORFS macro views without modifying final routed inputs."""
from pathlib import Path
import argparse,hashlib,json,os,re,subprocess
p=argparse.ArgumentParser();p.add_argument('--trial',required=True);p.add_argument('--candidate',required=True)
a=p.parse_args();assert re.fullmatch(r'attempt[0-9]+',a.trial);assert a.candidate in ['B256','B1024S']
base=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture')
physical=base/a.trial/'physical';r=json.loads((physical/'receipt.json').read_text());assert r['exit']==0 and r['candidate']==a.candidate
root=physical/'flow/results/nangate45'/('rarch157_'+a.candidate)/'base';out=Path.cwd()/'export';out.mkdir(exist_ok=False)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
protected=[root/('6_final.'+e)for e in ['odb','sdc','def','v','spef','gds']]
before={str(f):sha(f)for f in protected}
env=os.environ.copy();env.update(NUM_CORES='8',OMP_NUM_THREADS='8')
cmd=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(physical/'config.mk'),'WORK_HOME='+str(physical/'flow'),'do-generate_abstract']
with(out/'abstract.log').open('w')as f:r=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
assert before=={str(f):sha(f)for f in protected}
top='r_stream_sync'if a.candidate=='B1024S'else'r_stream'
views=[root/(top+'.lef'),root/(top+'_typ.lib')]
files={str(f):dict(bytes=f.stat().st_size,sha256=sha(f))for f in protected+views if f.exists()}
passed=r.returncode==0 and all(f.exists()and f.stat().st_size>0 for f in views)
(out/'EXPORT.json').write_text(json.dumps(dict(passed=passed,candidate=a.candidate,trial=a.trial,command=cmd,exit=r.returncode,source_final_unchanged=True,files=files,scope='actual abstract LEF and typical Liberty; full physical acceptance is separate'),indent=2)+'\n')
raise SystemExit(0 if passed else 1)
