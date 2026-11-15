from pathlib import Path
from hashlib import sha256
import json
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=ROOT/'hardware/service-controller-contracts.json';d=json.loads(p.read_text())
 new=dict(next(x for x in d['services'] if x['module']=='rope_s32_service_controller'))
 new.update(module='rope_native_service_controller',rtl='rtl/services/rope_native_service_controller.sv',
  descriptor={'schema':0x31455052,'abi':0x02500002,'opcode':1},
  scope='native descriptor wrapper over selected E; full graph and physical binding pending')
 new['rtl_sha256']=sha256((ROOT/new['rtl']).read_bytes()).hexdigest()
 d['services']=[x for x in d['services'] if x['module']!=new['module']]+[new]
 p.write_text(json.dumps(d,indent=2)+'\n')
if __name__=='__main__':main()
