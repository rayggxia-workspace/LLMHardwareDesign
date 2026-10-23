import unittest
from fractions import Fraction
import numpy as np
from quant_probe import signed_limbs,qfixed,packet,rne_fraction,integer_bias
class IntegerProbe(unittest.TestCase):
 def test_signed16_decomposition_full_domain(self):
  x=np.arange(-32768,32768,dtype=np.int64);digits=signed_limbs(x)
  self.assertTrue(all(np.max(abs(d.astype(np.int16)))<=64 for d in digits))
  self.assertTrue(np.array_equal(sum(d.astype(np.int64)*128**i for i,d in enumerate(digits)),x))
 def test_static_integer_RNE_signed_and_saturation(self):
  x=np.array([.5,1.5,2.5,-.5,-1.5,-2.5,200,-200],dtype=np.float32)
  q,n=qfixed(x,8,0);self.assertEqual(q.tolist(),[0,2,2,0,-2,-2,127,-127]);self.assertEqual(n,2)
 def test_packet_boundary(self):
  self.assertEqual([packet(n)for n in [0,1,1984,1985]],[0,128,2048,2176])
 def test_bias_before_rounding(self):
  result={'acc':np.array([[1]],dtype=np.int64),'e0':np.array([[-1]],dtype=np.int16),'units':np.array([[[-1]]],dtype=np.int16),'out':np.array([[0]],dtype=np.int8)}
  stats={'group':1,'early_group_RQ_mismatches':0};integer_bias(result,stats,np.array([.25],dtype=np.float32),np.array([0],dtype=np.int8))
  self.assertEqual(int(result['out'][0,0]),1);self.assertEqual(Fraction(int(result['acc'][0,0]))*Fraction(2)**int(result['e0'][0,0]),Fraction(3,4))
 def test_fraction_negative_ties(self):
  self.assertEqual([rne_fraction(Fraction(n,2))for n in [-5,-3,-1,1,3,5]],[-2,-2,0,0,2,2])
if __name__=='__main__':unittest.main()
