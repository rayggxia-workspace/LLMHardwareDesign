"""Diagnose exact source-clock restoration on an immutable actual GRT checkpoint."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess
from fixed_clock_routes import precheck,audit
p=argparse.ArgumentParser();p.add_argument('--physical',type=Path,required=True);a=p.parse_args()
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
S=a.physical;O=Path.cwd()/'clock-restore-probe';O.mkdir(exist_ok=False)
R=S/'flow/results/nangate45/r166_1024/base';odb=R/'5_1_grt.odb';defile=S/'CLOCK_before-detail.def'
names=['CLOCK_ROUTE_BINDING.json','CLOCK_BASELINE.json.gz','CLOCK_FIXED.def','CLOCK_NATIVE_NAMES.tsv','clock_source_names.tcl','CLOCK_LOCKED_CELLS.tsv']
inputs={str(f):sha(f)for f in [odb,defile]+[S/n for n in names]};result=dict(passed=False,inputs=inputs,physical=str(S),qualification=False,scope='Read-only diagnosis on failed before-detail checkpoint. Copied binding explicitly records diagnostic protocol adaptation; source physical/binding never changed. No final gate or qualification transfer.')
try:
 for name in names:shutil.copyfile(S/name,O/name)
 binding=json.loads((O/'CLOCK_ROUTE_BINDING.json').read_text());assert binding['qualification_transferred']is False
 binding['restoration_protocol']='exact-source-clock-restore-v1';binding['diagnostic_original_binding_sha256']=inputs[str(S/'CLOCK_ROUTE_BINDING.json')]
 (O/'CLOCK_ROUTE_BINDING.json').write_text(json.dumps(binding,indent=2)+'\n')
 result['precheck']=precheck(O,defile)
 t='set_thread_count 16\nread_db {'+str(odb)+'}\nread_def -floorplan_initialize {'+str(O/'CLOCK_FIXED.def')+'}\nwrite_def {'+str(O/'restored.def')+'}\n'
 (O/'restore.tcl').write_text(t)
 with(O/'restore.log').open('w')as log:r=subprocess.run(['openroad','-no_init','-exit',str(O/'restore.tcl')],stdout=log,stderr=subprocess.STDOUT)
 assert r.returncode==0
 result['restored_audit']=audit(O,O/'restored.def','before-detail');result['passed']=True
except Exception as error:result['error']=repr(error)
assert all(sha(Path(f))==v for f,v in inputs.items())
result['artifacts']={f.name:dict(sha256=sha(f),bytes=f.stat().st_size)for f in O.iterdir()if f.is_file()}
(O/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');raise SystemExit(0 if result['passed']else 1)
