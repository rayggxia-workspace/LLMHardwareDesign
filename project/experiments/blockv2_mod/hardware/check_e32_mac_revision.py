"""Verify unchanged macro pins, shared multipliers, numerical and lease evidence."""
from pathlib import Path
from hashlib import sha256
from collections import Counter
import json,shutil,xml.etree.ElementTree as ET
from rtl_ports import read
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evidence/architecture-revision-185'
def multipliers(filename,master):
 t=ET.parse(OUT/'e32-mac-audit-114620'/filename).getroot()
 types={x.get('id'):x for x in t.findall('./netlist/typetable/*')}
 m=next(x for x in t.findall('./netlist/module') if x.get('origName')==master)
 result=Counter()
 for x in m.iter():
  if x.tag in ('mul','muls') and all(y.tag!='const' for y in x):
   typ=types[x.get('dtype_id')];width=abs(int(typ.get('left','0'))-int(typ.get('right','0')))+1
   result[str(width)]+=1
 return dict(result)
def main():
 assert read((ROOT/'rtl/u0/e_s32_ap64.sv').read_text())==read((ROOT/'rtl/macros/e_s32_mac_ap64.sv').read_text())
 before=multipliers('baseline.xml','e_s32_native');after=multipliers('mod.xml','e_s32_mac_native')
 assert before==after=={'32':4,'33':4}
 assert 'E32_MAC_PASS commands=70648 max_k=65535 legacy_commands=204' in (OUT/'e32-mac-114616/run.log').read_text()
 assert 'E32_MAC_SELECTOR_PASS commands=70444 max_k=65535 competitor_excluded=1' in (OUT/'e32-mac-selector-114623/run.log').read_text()
 assert 'SHARED_E32_PASS clients=3 commands=96' in (OUT/'e32-selector-114622.log').read_text()
 files=['rtl/macros/e_s32_mac_ap64.sv','rtl/macros/e_s32_mac_native.sv',
  'rtl/u0/e_s32_ap64.sv','rtl/u0/e_s32_native.sv','rtl/resources/e32_service_selector.sv',
  'hardware/build_e32_mac_mod.py','hardware/rtl_ports.py',
  'evidence/architecture-revision-185/make_e32_mac_vectors.py',
  'evidence/architecture-revision-185/tb_e32_mac.sv','evidence/architecture-revision-185/tb_e32_mac_selector.sv',
  'evidence/architecture-revision-185/tb_e32_selector.sv','evidence/architecture-revision-185/e32-mac.sbatch',
  'evidence/architecture-revision-185/e32-mac-selector.sbatch','evidence/architecture-revision-185/e32-mac-audit.sbatch']
 hashes={}
 for name in files:
  p=ROOT/name;data=p.read_bytes();hashes[name]=sha256(data).hexdigest()
  dest=OUT/'e32-mac-114616/validated-revision'/name;dest.parent.mkdir(parents=True,exist_ok=True)
  if dest.exists():assert dest.read_bytes()==data,'validated source changed'
  else:shutil.copyfile(p,dest)
 result={'schema':'e32-mac-mod-evidence/1','functional_job':114616,'structure_job':114620,
  'lease_selector_job':114623,'legacy_selector_job':114622,'sources':hashes,
  'extra_macro_pins':0,'extra_macro_instances':0,'accumulator_state_bits':320,
  'baseline_multiply_expression_widths':before,'mod_multiply_expression_widths':after,
  'legacy_cycle_equivalence_commands':204,'max_k':65535,'mac_cases':6,
  'numeric_reference':'independent Python arbitrary-width integer product, sum, RNE and saturation',
  'arithmetic_scope':'elaborated expressions, not synthesized gate count or area',
  'full_attention_accepted':False,'whole_graph_accepted':False,'timing_calibrated':False}
 (OUT/'e32-mac-mod-receipt.json').write_text(json.dumps(result,indent=2)+'\n')
 p=ROOT/'hardware/e32-mac-mod-revision.json';d=json.loads(p.read_text())
 d['status']='macro and exclusive selector RTL unit verified; Attention service and whole-base integration pending'
 d['unit_evidence']={'path':'evidence/architecture-revision-185/e32-mac-mod-receipt.json',
                    'sha256':sha256((OUT/'e32-mac-mod-receipt.json').read_bytes()).hexdigest()}
 p.write_text(json.dumps(d,indent=2)+'\n')
 print('E32 MAC: unchanged pins and multiply expressions; legacy equivalence, exact full-K and exclusive lease verified')
if __name__=='__main__':main()
