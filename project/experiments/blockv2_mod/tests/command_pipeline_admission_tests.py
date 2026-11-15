"""Negative regressions: model-only evidence and stale sources must never admit RTL."""
import json,runpy,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
class Contract(unittest.TestCase):
 def reject(self,evidence,message):
  with tempfile.TemporaryDirectory(prefix='command-contract-') as d:
   root=Path(d);assembly=root/'assembly.json';proof=root/'proof.json';output=root/'output.json'
   assembly.write_text(json.dumps({'elaboration_accepted':True,'source_sha256':{}}))
   proof.write_text(json.dumps(evidence))
   with patch.object(sys,'argv',['seal','--assembly-receipt',str(assembly),'--evidence',str(proof),'--output',str(output)]):
    with self.assertRaisesRegex(ValueError,message):runpy.run_path('audits/command_pipeline_seal.py',run_name='__main__')
   self.assertFalse(output.exists())
 def test_model_peak_is_not_rtl_proof(self):
  self.reject({'passed':True,'evidence_kind':'tlm_behavior','observed_peak':32},'RTL behavior evidence required')
 def test_failed_rtl_is_not_accepted(self):
  self.reject({'passed':False,'evidence_kind':'rtl_behavior'},'failed evidence')
 def test_serial_activation_mutation_rejected(self):
  self.reject({'passed':True,'evidence_kind':'rtl_behavior','source_sha256':{},'verified_capabilities':{'activation_read_slots':1}},'capability mismatch activation_read_slots')
 def test_serial_weight_mutation_rejected(self):
  self.reject({'passed':True,'evidence_kind':'rtl_behavior','source_sha256':{},'verified_capabilities':{'weight_read_credits':1}},'capability mismatch weight_read_credits')
 def test_missing_capabilities_not_defaulted(self):
  self.reject({'passed':True,'evidence_kind':'rtl_behavior','source_sha256':{},'verified_capabilities':{}},'missing verified capabilities')

class DecodeChain(unittest.TestCase):
 def check(self, mutation=None, error=None):
  import hashlib
  with tempfile.TemporaryDirectory(prefix='decode-chain-') as d:
   root=Path(d)
   for h in (512,513):
    (root/f'{h}-execution').mkdir();(root/f'{h}-assets').mkdir()
    r={'status':'all_instructions_executed','completed_calls':1,'native_calls':1,
       'plan_sha256':str(h),'committed_state':{'sha256':'actual-first-state'},
       'outputs':[{'value':'logits','sha256':'actual-first-logits'}],'time_ps':10}
    for k in ('core_ps','dram_config_sha256','dram_library_sha256','sram_config_sha256','source_sha256'):r[k]='same'
    rp=root/f'{h}-execution/receipt.json';rp.write_text(json.dumps(r))
    c={'all_exported_values_bit_exact':True,'values_checked':list(range(73)),
       'plan_sha256':str(h),'execution_receipt_sha256':hashlib.sha256(rp.read_bytes()).hexdigest()}
    (root/f'{h}-bit-exact.json').write_text(json.dumps(c))
    a={'plan_sha256':str(h),'regions':[]}
    if h==512:
     for i in range(72):
      name=f'past_{i}';(root/f'{h}-assets'/name).write_bytes(bytes(4))
      a['regions'].append({'name':name,'file':name,'sha256':hashlib.sha256(bytes(4)).hexdigest(),
        'origin':{'standard_quick_frozen_zero_KV':True,'history_positions':512}})
     (root/f'{h}-assets/token').write_bytes((840).to_bytes(4,'little'))
     a['regions'].append({'name':'input_ids','file':'token','origin':{'token':840}})
    else:
     a['source_state_sha256']='actual-first-state'
     a['regions'].append({'name':'input_ids','origin':{'source_logits_sha256':'actual-first-logits'}})
     if mutation:mutation(a)
    (root/f'{h}-assets/assets.json').write_text(json.dumps(a))
   with patch.object(sys,'argv',['accept',str(root)]):
    if error:
     with self.assertRaisesRegex(ValueError,error):runpy.run_path('audits/command_pipeline_accept.py',run_name='__main__')
     self.assertFalse((root/'two-step-receipt.json').exists())
    else:runpy.run_path('audits/command_pipeline_accept.py',run_name='__main__')
 def test_causal_chain(self):self.check()
 def test_independent_second_decode_rejected(self):
  self.check(lambda a:a.update(source_state_sha256='independent-zero-state'),'step2 disconnected')
 def test_fixed_second_token_rejected(self):
  self.check(lambda a:a['regions'][0]['origin'].update(source_logits_sha256='fixed-token'),'step2 token disconnected')


class ProductionAdmission(unittest.TestCase):
 def test_old_base_rejected_before_product_join(self):
  from native_product_binding import validate
  with self.assertRaisesRegex(ValueError,'hardware does not certify'):
   validate({},'old-plan',{})
 def test_old_base_rejected_before_package_emission(self):
  from native_machine_package import package
  with tempfile.TemporaryDirectory(prefix='old-package-') as d:
   output=Path(d)/'package'
   plan={'schema':'macro-native-selected-plan/1','calls':[],'hardware':{}}
   with self.assertRaisesRegex(ValueError,'hardware does not certify'):
    package(plan,output,18503)
   self.assertFalse(output.exists())

if __name__=='__main__':unittest.main()
