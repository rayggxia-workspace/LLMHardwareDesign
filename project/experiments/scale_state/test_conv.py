import unittest
import numpy as np
from conv import exponent,encode,run_chain,silu
class ConvContract(unittest.TestCase):
 def test_exact_taps_nonzero_initial_and_continuity(self):
  x=np.array([[[5,6,7],[4,3,2]]],dtype=np.int16);h=np.array([[[1,2,3,4],[1,1,1,1]]],dtype=np.int16);w=np.array([[1,-2,3,-4],[127,-127,127,-127]],dtype=np.int8)
  acc,states,terms=run_chain(x,h,w)
  self.assertEqual(acc[0,0,0],2-6+12-20);self.assertEqual(terms,24);np.testing.assert_array_equal(states[1,0,0],[2,3,4,5])
  a,s,_=run_chain(x[:,:,:1],h,w);b,_,_=run_chain(x[:,:,1:],s[-1],w);np.testing.assert_array_equal(np.concatenate([a,b],axis=2),acc)
 def test_static_scales_clip_and_zero(self):
  e=exponent(np.zeros((1,2,4)),127,(0,2));np.testing.assert_array_equal(e,[0,0])
  q,c=encode(np.array([-.5,1.5,2.5,200]),0,127);np.testing.assert_array_equal(q,[0,2,2,127]);self.assertEqual(c,1)
 def test_I32_max_H16_W8_and_signed(self):
  x=np.full((1,1,2),32767,dtype=np.int16);h=np.full((1,1,4),32767,dtype=np.int16);w=np.full((1,4),127,dtype=np.int8)
  a,_,_=run_chain(x,h,w);self.assertTrue(np.all(a==4*32767*127));self.assertLess(int(a.max()),2**31)
 def test_silu_stable_domain(self):
  x=silu(np.array([-1000.,0.,1000.]));self.assertTrue(np.isfinite(x).all());np.testing.assert_array_equal(x,[0.,0.,1000.])
 def test_invalid_shape_and_float_rejected(self):
  with self.assertRaises(ValueError):run_chain(np.zeros((1,2,1)),np.zeros((1,2,4)),np.zeros((2,4),dtype=np.int8))
if __name__=='__main__':unittest.main()
