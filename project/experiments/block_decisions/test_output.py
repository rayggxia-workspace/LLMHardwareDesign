import unittest
from fractions import Fraction
import numpy as np
from output import shift,quant,delta_row,packet
class OutputContract(unittest.TestCase):
 def test_ties_and_large_signed_values(self):
  for x in [-2**55-3,-7,-5,-3,-1,0,1,3,5,7,2**55+3]:
   for n in range(-3,12):self.assertEqual(shift(x,n),round(Fraction(x)*Fraction(2)**-n))
 def test16_same_range_does_not_hide_outliers(self):
  acc=np.array([[127,128,-128,-129]]);u=np.zeros_like(acc);e8=np.zeros_like(acc);e16=e8-8
  c,s,n=quant(acc,u,e8,-128,127);d,t,m=quant(acc,u,e16,-32768,32512)
  self.assertEqual(s,2);self.assertEqual(t,2);self.assertTrue(np.array_equal(c*256,d))
 def test_delta_derived_from_integer_complete_tile(self):
  a=np.array([[1,2],[1000,-1000],[0,0]],dtype=np.int64);u=np.zeros_like(a);base=np.array([0,0]);d,trials,terms=delta_row(a,u,base)
  self.assertEqual(d[1],3);self.assertEqual(d[2],0)
  for i in range(2):self.assertTrue(all(-128<=shift(int(x),int(e)+int(d[i])-int(v))<=127 for x,v,e in zip(a[i],u[i],base)))
  self.assertGreater(terms,0)
 def test_metadata_can_cross_packet_boundary(self):
  self.assertEqual(packet(16+16+32),128);self.assertEqual(packet(16+16+32+1),192);self.assertEqual(packet(32+16+32),192)
if __name__=='__main__':unittest.main()
