import copy,json,sys,tkinter
from pathlib import Path
sys.path.insert(0,str(Path('project/experiments/control_v1').resolve()))
from s_reset_repair import config
p=Path('work/YUZE-LU/162/continuation-proof-18/s-reset-branch-diagnostic-03/reset-branch-measurements.json')
data=json.loads(p.read_bytes())
for count in (96,128):
 text,rows=config(p.read_bytes(),count)
 assert [r['index']for r in rows]==[0,2,3,4,5]
 assert len(text.splitlines())==9
for field,value in [('master','BUF_X1'),('net','wrong'),('instance','x;exec bad'),('minimum_setup_ns',1.9)]:
 d=copy.deepcopy(data);d['branches'][0][field]=value
 try:config(json.dumps(d).encode(),96)
 except AssertionError:pass
 else:raise AssertionError(field)
d=copy.deepcopy(data);d['branches'][1]['minimum_hold_ns']=-.2
try:config(json.dumps(d).encode(),96)
except AssertionError:pass
else:raise AssertionError('extra negative branch')
for flag in ('passed','diagnostic_only','no_database_or_constraint_mutation'):
 d=copy.deepcopy(data);d[flag]=False
 try:config(json.dumps(d).encode(),96)
 except AssertionError:pass
 else:raise AssertionError(flag)
try:config(p.read_bytes(),64)
except AssertionError:pass
else:raise AssertionError('count')
assert tkinter.Tcl().call('info','complete',Path('project/experiments/control_v1/s_reset_delay.tcl').read_text())
print('PASS: actual source125 selects only five fast AOI branches for96/128; nine invalid evidence/config cases rejected; Tcl complete. No EDA execution claimed.')
