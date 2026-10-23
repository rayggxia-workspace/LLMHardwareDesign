import copy
import unittest
import numpy as np
import torch
from replay import partials,state_window


class Reference(unittest.TestCase):
    def fixture(self):
        g={'group':0,'A':torch.tensor([[1,-3]],dtype=torch.int8),'B':torch.tensor([[5],[-2]],dtype=torch.int8),
           'accumulator':torch.tensor([[11]],dtype=torch.int32),'activation_scale':torch.tensor([[.5]],dtype=torch.float32),
           'weight_scale':torch.tensor([.25],dtype=torch.float32)}
        return {str(i):{'boundary':'post activation input; INT32 partials before FP32 scale/sum','input_shape':[1,1,2],
            'groups':[copy.deepcopy(g)],'bias':None,'output':torch.tensor([[1.375]],dtype=torch.float16)} for i in range(6)}

    def test_integer_known_and_mutation(self):
        payload=self.fixture();self.assertEqual(partials(payload)['INT64_partial_values'],6)
        payload['0']['groups'][0]['accumulator'][0,0]+=1
        with self.assertRaises(AssertionError):partials(payload)

    def test_state_zero_and_nonzero_decay(self):
        payload={'query':torch.ones(1,1,1,2),'key':torch.zeros(1,1,1,2),'value':torch.zeros(1,1,1,2),
            'g':torch.tensor([[[-np.log(2)]]]),'beta':torch.ones(1,1,1),'initial_state':torch.ones(1,1,2,2),
            'output':torch.ones(1,1,1,2)/np.sqrt(2+1e-6)/np.sqrt(2),'final_state':torch.ones(1,1,2,2)*.5}
        out,final=state_window(payload)
        self.assertLess(out['relative_l2'],1e-6);self.assertLess(final['relative_l2'],1e-6)


if __name__=='__main__':unittest.main()
