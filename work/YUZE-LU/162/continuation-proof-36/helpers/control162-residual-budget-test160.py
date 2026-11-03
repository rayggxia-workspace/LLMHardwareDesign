"""Independent arithmetic, provenance and inconsistent-measurement controls."""
import sys,tempfile,json,hashlib,copy
from pathlib import Path
root=Path(r'D:\Data\电路实验\LLMHardwareDesign-worktrees\issue-162-control\project\experiments\control_v1');sys.path.insert(0,str(root))
from placement_residual_budget import budgets
drivers={'net_1':dict(driver=dict(instance='a',pin='p'),physical_driver=dict(max_capacitance_ff=100.))}
row=dict(net='net_1',driver=dict(instance='a',pin='p'),max_capacitance_ff=100.,native_ground_cap_ff=20.,minimum_input_pin_cap_ff=5.)
base=dict(passed=True,diagnostic_executed=True,whole_system_qualified=False,placements=[dict(rows=[row]),dict(rows=[copy.deepcopy(row)])])
def mutate(fn):
 d=copy.deepcopy(base);fn(d);return d
cases=[('false-execution',mutate(lambda d:d.update(passed=False))),('wrong-scope',mutate(lambda d:d.update(whole_system_qualified=True))),('empty',mutate(lambda d:d.update(placements=[]))),('driver',mutate(lambda d:d['placements'][0]['rows'][0]['driver'].update(instance='wrong'))),('limit',mutate(lambda d:d['placements'][0]['rows'][0].update(max_capacitance_ff=101.))),('negative',mutate(lambda d:d['placements'][0]['rows'][0].update(native_ground_cap_ff=-1.))),('impossible',mutate(lambda d:d['placements'][0]['rows'][0].update(native_ground_cap_ff=96.))),('inconsistent',mutate(lambda d:d['placements'][1]['rows'][0].update(native_ground_cap_ff=21.))),('duplicate',mutate(lambda d:d['placements'][0]['rows'].append(copy.deepcopy(row))))]
with tempfile.TemporaryDirectory(prefix='ctl162-budget160-')as directory:
 p=Path(directory)/'native-pin-load.json';receipt=p.parent/'receipt.json'
 def write(d):
  p.write_text(json.dumps(d));receipt.write_text(json.dumps(dict(passed=True,stage='minimum-native-pin-capacitance-failure-only',outputs={p.name:hashlib.sha256(p.read_bytes()).hexdigest()})))
 write(base);assert budgets(p,drivers)[0]=={'net_1':75.}
 for name,d in cases:
  write(d)
  try:budgets(p,drivers)
  except AssertionError:pass
  else:raise AssertionError('Control accepted '+name)
 write(base);p.write_text(p.read_text()+' ')
 try:budgets(p,drivers)
 except AssertionError:pass
 else:raise AssertionError('Tampered bytes accepted')
print(json.dumps(dict(passed=True,independent_arithmetic=True,negative_controls=len(cases)+1,whole_system_qualified=False)))
