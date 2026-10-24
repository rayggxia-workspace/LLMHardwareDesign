"""Bounded synthetic integer tests; no model files or real tensors loaded."""
import importlib.util
from pathlib import Path
from fractions import Fraction
import unittest
import numpy as np

spec=importlib.util.spec_from_file_location('granite_numeric',Path(__file__).with_name('granite_numeric.py'))
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)

class IntegerRouterTests(unittest.TestCase):
    def test_rne_signed_against_fraction(self):
        for d in range(1,20):
            for n in range(-100,101):self.assertEqual(g.rne_div(n,d),round(Fraction(n,d)))
        with self.assertRaises(ValueError):g.rne_div(1,0)

    def test_signed_shifts(self):
        for n in (-65,-64,-3,-1,0,1,3,64,65):
            for shift in range(-5,8):
                self.assertEqual(g.rne_shift(n,shift),round(Fraction(n,1)*(Fraction(1,2)**shift)))

    def test_s16_digit_extrema(self):
        a=np.asarray([[-32767,-16384,-128,-127,-1,0,1,127,128,16384,32767]],dtype=np.int16)
        digits=g.base128_digits(a)
        restored=sum(digits[i].astype(np.int64)*(1<<(7*i)) for i in range(3))
        np.testing.assert_array_equal(a,restored)
        self.assertLessEqual(np.max(np.abs(digits.astype(np.int64))),127)
        with self.assertRaises(ValueError):g.base128_digits([-32768])

    def test_s8x9_lowering_full_k(self):
        a=np.asarray([[-32767,32767,-32767,1],[32767,-32767,32767,-1]],dtype=np.int16)
        w=np.asarray([[32767,-32767,32767,-1],[-32767,-32767,-32767,1]],dtype=np.int16)
        actual,partial=g.lowered16_dot(a,w)
        expected=np.asarray([[sum(int(x)*int(y) for x,y in zip(row,col)) for col in w] for row in a])
        np.testing.assert_array_equal(actual,expected)
        self.assertEqual(partial.shape,(9,2,2))
        self.assertGreater(np.max(np.abs(actual)),(1<<31)-1)

    def test_alignment_exact_peroutput_exponents(self):
        dot=np.asarray([[7,-4,3],[1,2,-6]],dtype=np.int64)
        common,exps,width=g.align_logits(dot,[-5,-6],[-8,-7,-6])
        for row in range(2):
            for col in range(3):
                expected=Fraction(int(dot[row,col]),1)*Fraction(2)**([-5,-6][row]+[-8,-7,-6][col])
                self.assertEqual(Fraction(int(common[row,col]),1)*Fraction(2)**int(exps[row]),expected)
        self.assertEqual(len(width),2)

    def test_top8_exact_ties_and_s64_minimum(self):
        x=np.zeros((1,40),dtype=np.int64);x[0,39]=np.iinfo(np.int64).min
        np.testing.assert_array_equal(g.integer_top8(x)[0],np.arange(8))
        x[0,15]=1;self.assertEqual(g.integer_top8(x)[0,0],15)

    def test_gate_equal_and_extreme(self):
        lut=g.compile_lut()
        x=np.zeros((2,40),dtype=np.int64);x[1,0]=100000
        ids=g.integer_top8(x)
        gate,index,clips=g.integer_softmax(x,[0,0],ids,lut)
        np.testing.assert_array_equal(gate[0],np.full(8,4096))
        np.testing.assert_array_equal(np.sum(gate,axis=1),[32768,32768])
        self.assertEqual(clips,7)
        self.assertEqual(int(index[1,1]),2048)

    def test_scale_no_percentile_and_saturation(self):
        exp=g.compile_exponent([127.,128.,0.],8)
        np.testing.assert_array_equal(exp,[0,1,0])
        q,sat=g.encode(np.asarray([-.5,-1.5,.5,1.5,500.]),0,8)
        np.testing.assert_array_equal(q,[0,-2,0,2,127])
        self.assertEqual(int(np.count_nonzero(sat)),1)

    def test_rank_certificate_rejects_uncertain_or_clipped(self):
        aq=np.ones((1,16),dtype=np.int8)*100
        wq=np.zeros((40,16),dtype=np.int8);wq[32:]=80
        dot=aq.astype(np.int64)@wq.astype(np.int64).T
        ids=g.integer_top8(dot)
        cert,b=g.certify_top8(dot,[0],np.zeros(40,dtype=np.int16),aq,wq,ids,[False])
        self.assertTrue(bool(cert[0]))
        self.assertFalse(bool(g.certify_top8(dot,[0],np.zeros(40,dtype=np.int16),aq,wq,ids,[True])[0][0]))
        tied=np.zeros((1,40),dtype=np.int64)
        self.assertFalse(bool(g.certify_top8(tied,[0],np.zeros(40,dtype=np.int16),aq,wq,g.integer_top8(tied),[False])[0][0]))
        self.assertGreater(int(b.max()),0)

    def test_w8_and_w16_full_k_bounds(self):
        self.assertEqual(1536*127**2,24774144)
        self.assertLess(1536*127**2,2**31)
        self.assertGreater(1536*32767**2,2**31)
        self.assertLess(1536*32767**2,2**41)

if __name__=='__main__':unittest.main()
