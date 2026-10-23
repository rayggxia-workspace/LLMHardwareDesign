import unittest
from fractions import Fraction
import numpy as np
from bounds import pv32
class ConditionalBounds(unittest.TestCase):
 def test_actual_i32_limb_kernel_and_guard(self):
  p=np.zeros((1,1,4128),dtype=np.int64);p[0,0,:2]=[32767,2066];v=np.zeros((4128,1),dtype=np.int64);v[:2,0]=[24512,-32767]
  got,stats=pv32(p,v,16,16,np.array([34833]));self.assertEqual(int(got[0,0,0]),32767*24512-2066*32767);self.assertEqual(stats['S8_matmul_passes'],9)
  with self.assertRaisesRegex(ValueError,'P sum guard'):pv32(np.array([[[32767,32767]]]),np.array([[1],[1]]),16,16,np.array([32770]))
 def test_signed16_limb_absolute_bound_exhaustive(self):
  x=np.arange(-32767,32768,dtype=np.int64);d0=((x+64)%128)-64;d1=(((x-d0)//128+64)%128)-64;d2=(x-d0-128*d1)//16384
  self.assertTrue(np.array_equal(d0+128*d1+16384*d2,x))
  self.assertLessEqual(int(np.max(abs(d0))),64);self.assertLessEqual(int(np.max(abs(d1))),64);self.assertLessEqual(int(np.max(abs(d2))),2)
  self.assertEqual(int(np.max(abs(d0)+128*abs(d1)+16384*abs(d2))),41024)
  p=np.arange(32768,dtype=np.int64);digits=[(p>>(7*i))&127 for i in range(3)]
  self.assertTrue(np.array_equal(sum(d*128**i for i,d in enumerate(digits)),p));self.assertTrue(all(d.max()<=127 for d in digits))
 def test_integer32_guard_has_context_limit(self):
  budget=32768+(4128+1)//2+1;self.assertEqual(budget,34833);self.assertLess(budget*41024,1<<31)
  self.assertGreater((32768+(40000+1)//2+1)*41024,1<<31)
 def test_exact_probability_rounding_sum_and_resolution(self):
  for f in [7,15]:
   for n in [1,3,7,128,256,1024,4128,65535]:
    code=max(0,min(2**f-1,round(Fraction(2**f,n))));self.assertLessEqual(n*code,2**f+(n+1)//2+1)
  self.assertEqual(round(Fraction(128,256)),0)
if __name__=='__main__':unittest.main()
