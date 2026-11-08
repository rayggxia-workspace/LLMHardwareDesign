"""Audit the frozen bounded profile against actual RTL and codec inventory."""
import json,re,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def check():
 d=json.loads((HERE/'freeze.json').read_text())
 isa=json.loads((ROOT/'project/control_isa_v0_1/isa.json').read_text())
 for role,key in (('mother','mc'),('local','lc')):
  code=(ROOT/f'project/control_rtl_min_v0_1/{key}_min_controller.sv').read_text()
  actual={int(x,16) for x in re.findall(r"8'h([0-9a-fA-F]+)(?=[:,])",code)}
  expected=set(d[role+'_opcodes'].values())
  assert actual==expected,(role,actual,expected)
  assert all(any(x['name']==name and x['opcode']==value for x in isa['opcodes']) for name,value in d[role+'_opcodes'].items())
 assert {x['type'] for x in d['native_profiles']}==set('PUCFJ')
 assert d['mother_targets']==2 and d['instruction_bits']==64
 assert d['clock_period_ns']==json.loads((ROOT/'project/control_native_timing_v1/constraints.json').read_text())['period_ns']
 assert d['pm']['bytes_each']>=max(d['image_maximum_bytes'].values())
 assert not d['production_ready']
 return {'frozen_profile_checked':True,'implemented_opcodes':len(d['mother_opcodes'])+len(d['local_opcodes']),
         'native_types':5,'targets':2,'period_ns':d['clock_period_ns'],
         'spec_sha256':hashlib.sha256((HERE/'freeze.json').read_bytes()).hexdigest()}
if __name__=='__main__':print(json.dumps(check(),indent=2))
