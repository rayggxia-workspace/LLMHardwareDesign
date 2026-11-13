import unittest
from copy import deepcopy
from acceptance import assess


class Acceptance(unittest.TestCase):
    def fixture(self):
        return {'checkpoint_sha256':'model','token_ids_sha256':'tokens','batch':1,'prompt_tokens':512,
          'decode_steps':128,'quality_gate_id':'fixed','numeric_passed':True,'best_mapping_evidence':'search-receipt',
          'complete_energy_scope':True,'energy_calibration_sha256':'activity-library-memory',
          'coefficient_class':'measured-calibrated','decode_tokens_per_second':10.,
          'joules_per_decode_token':1.,'timing_backend':'systemc','native_optimized_configuration':True}

    def test_missing_energy_or_weak_peer_never_passes(self):
        for field,value in [('coefficient_class','synthetic'),('complete_energy_scope',False),
                            ('energy_calibration_sha256',None),('numeric_passed',False),
                            ('best_mapping_evidence',None),('prompt_tokens',2),
                            ('decode_tokens_per_second',float('nan')),('native_optimized_configuration',False)]:
            a=self.fixture();b=self.fixture();b[field]=value
            self.assertFalse(assess(a,b)['passed'],field)

    def test_real_regression_is_not_hidden(self):
        a=self.fixture();b=self.fixture();a['decode_tokens_per_second']=9
        self.assertFalse(assess(a,b)['passed'])
        a['decode_tokens_per_second']=11;a['joules_per_decode_token']=1.1
        self.assertFalse(assess(a,b)['passed'])
        a['joules_per_decode_token']=.9
        self.assertTrue(assess(a,b)['passed'])


if __name__=='__main__':unittest.main()
