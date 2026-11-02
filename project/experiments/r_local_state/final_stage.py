"""Dependency-ready final stages; no running or failed producer can qualify."""
from pathlib import Path
import argparse,json,subprocess,hashlib
p=argparse.ArgumentParser();p.add_argument('--physical',type=Path,required=True);p.add_argument('--capacity',type=int,required=True);p.add_argument('--stage',choices=['evaluate','build','geometry','native'],required=True);p.add_argument('--threads',type=int,choices=[1,16],default=1);a=p.parse_args()
P=Path(__file__).resolve().parent;O=Path.cwd()/'STAGE_RECEIPT.json';rec={'passed':False,'stage':a.stage,'physical':str(a.physical),'capacity':a.capacity}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
try:
 producer=json.loads((a.physical/'receipt.json').read_text());assert producer['exit']==0,'physical producer failed'
 rec['producer_sha256']=sha(a.physical/'receipt.json')
 R=a.physical/'flow/results/nangate45'/('r166_'+str(a.capacity))/'base'
 if a.stage in ['build','native']:
  m=json.loads((a.physical/'flow/logs/nangate45'/('r166_'+str(a.capacity))/'base/6_report.json').read_text())
  assert m['finish__timing__setup__ws']>=0 and m['finish__timing__hold__ws']>=0,'final extracted timing failed'
  assert all(m[k]==0 for k in ['finish__timing__drv__setup_violation_count','finish__timing__drv__hold_violation_count','finish__timing__drv__max_cap','finish__timing__drv__max_slew']),'final electrical/timing counts failed'
  cmd=(['python3',str(P/'netlist_test.py'),'--capacity',str(a.capacity),'--netlist',str(R/'6_final.v'),'--threads',str(a.threads),'--build-only']if a.stage=='build'else['python3',str(P/'native_complete.py'),'--capacity',str(a.capacity),'--physical',str(a.physical)])
 else:
  runner='evaluate.py'if a.stage=='evaluate'else'route_geometry.py'
  cmd=['python3',str(P/runner),'--capacity',str(a.capacity),'--physical',str(a.physical)]
 rec['command']=cmd;v=subprocess.run(cmd);rec['exit']=v.returncode;rec['passed']=v.returncode==0
except Exception as e:rec['error']=repr(e)
O.write_text(json.dumps(rec,indent=2)+'\n');raise SystemExit(0 if rec['passed']else 1)
