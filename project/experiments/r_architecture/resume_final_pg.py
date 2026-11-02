"""Rerun final extraction/LEC/STA/GDS on an isolated routed copy with PG closure."""
from pathlib import Path
import hashlib,json,os,re,shutil,subprocess
base=Path('/public/home/yuzelu/project-circuit/LLMHardwareDesign/issue-157-r-architecture')
src=base/'attempt089/physical';dst=Path.cwd()/'physical'
r=json.loads((src/'receipt.json').read_text());assert r['exit']==0 and r['candidate']=='B256'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb')as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
protected=[p for p in (src/'flow/results/nangate45/rarch157_B256/base').glob('6_*')if p.is_file()]
protected += [src/'config.mk',src/'input.sdc']
before={str(p):sha(p)for p in protected}
dst.mkdir(exist_ok=False)
subprocess.run(['cp','-a','--reflink=auto',str(src/'flow'),str(dst/'flow')],check=True)
# Keep routed 6_1_fill inputs. Remove only stale final products in this copy.
for p in (dst/'flow').rglob('*'):
 if p.is_file()and (p.name.startswith('6_final.')or p.name.startswith('6_report.')or p.name.startswith('6_drc.')):p.unlink()
for n in ['input.sdc','IMPLEMENTATION.json']:shutil.copyfile(src/n,dst/n)
shutil.copyfile(Path(__file__).parent/'final_pg.tcl',dst/'final_pg.tcl')
config=(src/'config.mk').read_text()+'\nexport PRE_FINAL_REPORT_TCL = '+str(dst/'final_pg.tcl')+'\n'
(dst/'config.mk').write_text(config)
env=os.environ.copy();env.update(NUM_CORES='16',OMP_NUM_THREADS='16')
cmd=['make','-C','/OpenROAD-flow-scripts/flow','DESIGN_CONFIG='+str(dst/'config.mk'),'WORK_HOME='+str(dst/'flow'),'do-6_report']
with(dst/'flow.log').open('w')as f:result=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT)
assert before=={str(p):sha(p)for p in protected}
rec=dict(candidate='B256',capacity=256,exit=result.returncode,commands=[cmd],source=str(src),source_unchanged=True,source_sha256=before,change='added-buffer PG connectivity only; final extraction, LEC and STA rerun',expected_added_buffers=168,pg_hook_observed='R157_FINAL_PG_CONNECTED=168'in(dst/'flow.log').read_text(),qualification_transferred=False)
(dst/'receipt.json').write_text(json.dumps(rec,indent=2)+'\n')
assert rec['pg_hook_observed'];raise SystemExit(result.returncode)
