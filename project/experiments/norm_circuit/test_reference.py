import unittest
from verify import oracle,check
from m_verify import rne
class ReferenceTests(unittest.TestCase):
 def test_zero_den(self):self.assertEqual(oracle({'h':1,'x':[0],'gamma':[1],'epsilon':0})[0],2)
 def test_bad_h(self):self.assertEqual(oracle({'h':0})[0],1)
 def test_ties(self):self.assertEqual([rne(n,1)for n in(-5,-3,3,5)],[-2,-2,2,2])
 def test_wide_shift(self):self.assertEqual(rne(-(1<<63),130),0)
 def test_negative_shift(self):
  with self.assertRaises(ValueError):rne(1,-1)
 def test_min_square_sign(self):
  st,x=oracle({'h':1,'x':[-(1<<31)],'gamma':[1<<20],'epsilon':17});self.assertEqual((st,x),(0,[-4096]))
 def test_negative_gamma(self):
  st,x=oracle({'h':1,'x':[1<<20],'gamma':[-(1<<20)],'epsilon':17});self.assertEqual((st,x),(0,[-4096]))
 def test_missing_execution(self):
  with self.assertRaises(ValueError):check([{'name':'x'}],[])
if __name__=='__main__':unittest.main()
