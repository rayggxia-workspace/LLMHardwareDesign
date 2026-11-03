"""Exercise actual native keepout lifecycle across separate PRE/POST scopes."""
from pathlib import Path
from decimal import Decimal
import argparse,hashlib,json,re,subprocess
from short_obstruction_hooks import hooks
p=argparse.ArgumentParser();p.add_argument('--physical',type=Path,required=True);p.add_argument('--diagnosis',type=Path,required=True);a=p.parse_args()
sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
odb=a.physical/'flow/results/nangate45/r166_1024/base/6_final.odb';report=a.diagnosis/'complete.rpt';r=json.loads((a.diagnosis/'receipt.json').read_text())
assert r['passed']is False and r['original_odb_sha256']==sha(odb)and r['native_report_sha256']==sha(report)
rows=re.findall(r'violation type: Short\s+srcs: net:(\S+) net:(\S+)\s+bbox = \(([-\d.]+), ([-\d.]+)\) - \(([-\d.]+), ([-\d.]+)\) on Layer (\w+)',report.read_text());assert len(rows)==r['native_drc_count']and 0<len(rows)<=64
O=Path.cwd()/'short-hook-probe';O.mkdir(exist_ok=False);module=Path(__file__).with_name('short_obstruction_hooks.py');inputs={str(f):sha(f)for f in [odb,report,a.diagnosis/'receipt.json',module]}
t='set_thread_count 16\nread_db {'+str(odb)+'}\nwrite_def {'+str(O/'before.def')+'}\nproc r166_pre {file} {source $file}\nproc r166_post {file} {source $file}\n'
for label,items in [('zero',[]),('five',rows)]:
 d=O/label;d.mkdir();before,after=hooks(d,items,Decimal('.14'));(d/'before.tcl').write_text(before);(d/'after.tcl').write_text(after)
 t+='r166_pre {'+str(d/'before.tcl')+'}\nr166_post {'+str(d/'after.tcl')+'}\nwrite_def {'+str(d/'after.def')+'}\n'
(O/'probe.tcl').write_text(t)
with(O/'probe.log').open('w')as log:r=subprocess.run(['openroad','-no_init','-exit','probe.tcl'],cwd=O,stdout=log,stderr=subprocess.STDOUT)
assert all(sha(Path(n))==h for n,h in inputs.items());checks={};artifacts={}
if r.returncode==0:
 for label,count in [('zero',0),('five',len(rows))]:
  d=O/label;v=(d/'SHORT_TEMP_OBSTRUCTIONS_REMOVED.tsv').read_text().split()
  checks[label]=len(v)==3 and int(v[0])==count and v[1]==v[2]and sha(O/'before.def')==sha(d/'after.def')
for f in O.rglob('*'):
 if f.is_file():artifacts[str(f.relative_to(O))]=dict(sha256=sha(f),bytes=f.stat().st_size)
(O/'receipt.json').write_text(json.dumps(dict(passed=r.returncode==0 and checks and all(checks.values()),native_exit=r.returncode,physical=str(a.physical),inputs=inputs,hook_sha256=sha(module),checks=checks,artifacts=artifacts,qualification=False,scope='Actual native PRE/POST in different procedure scopes, zero/five keepouts, exact original full native DEF bytes restored. Source untouched. Hook component only; final routing/timing/power/native/GDS/function gates remain mandatory.'),indent=2)+'\n');raise SystemExit(0 if r.returncode==0 and checks and all(checks.values())else 1)
