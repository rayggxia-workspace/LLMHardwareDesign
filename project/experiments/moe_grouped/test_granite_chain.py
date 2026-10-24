"""Small synthetic integer boundaries; no real model/capture execution locally."""
import importlib.util
from pathlib import Path
from collections import Counter
from fractions import Fraction
import math
import unittest
import numpy as np

spec=importlib.util.spec_from_file_location('granite_chain74',Path(__file__).with_name('granite_chain.py'))
g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)

class IntegerTests(unittest.TestCase):
    def test_signed_RNE_independent_fraction(self):
        for n in range(-101,102):
            for d in range(1,19):self.assertEqual(g.rdiv(n,d),round(Fraction(n,d)))
        for n in (-255,-129,-1,0,1,129,255):
            for s in range(-4,9):self.assertEqual(g.scalar_shift(n,s),round(Fraction(n,1)*Fraction(2)**(-s)))

    def test_dynamic_minimal_shift_boundaries(self):
        x=np.asarray([[127,0],[128,0],[254,0],[255,0],[-255,0]],np.int32)
        a,d=g.encode_dynamic(x,8,Counter())
        np.testing.assert_array_equal(d,[0,1,1,2,2])
        np.testing.assert_array_equal(a[:,0],[127,64,127,64,-64])

    def test_router16_all9_digits_actual(self):
        a=np.asarray([[-32767,32767,-16384,128],[32767,-32767,16384,-128]],np.int16)
        w=np.repeat(np.asarray([[32767,-32767,128,-1]],np.int16),40,axis=0)
        ops=Counter();value,p=g.router_dot(a,w,16,ops)
        expected=np.asarray([[sum(int(x)*int(y) for x,y in zip(row,col)) for col in w] for row in a],np.int64)
        np.testing.assert_array_equal(value,expected)
        self.assertEqual(p.shape,(9,2,40))
        self.assertEqual(ops['router_S8_MACs'],9*2*40*4)
        self.assertGreater(int(np.max(np.abs(value))),(1<<31)-1)

    def test_declared_unsigned_gate_domain(self):
        q=g.mul(np.array([100],np.int32),np.array([32768],np.uint16),None,32,16,b_unsigned=True)
        np.testing.assert_array_equal(q,[3276800])
        with self.assertRaises(OverflowError):g.mul([100],[32768],None,32,16)
        with self.assertRaises(OverflowError):g.mul([1<<32],[1],None,32,32)

    def test_integer_norm_stats_and_RNE(self):
        x=np.asarray([[4096,-8192,2048,1024]],np.int32);gamma=np.asarray([1<<20]*4,np.int32)
        out,stats=g.norm(x,gamma,17,Counter())
        total=sum(int(v)**2 for v in x[0]);variance=total//4+17;den=math.isqrt(variance<<40)
        expected=[round(Fraction((int(v)*(1<<20))<<12,den)) for v in x[0]]
        np.testing.assert_array_equal(out,[expected])
        self.assertEqual(int(stats['sumsq_lo_u64'][0]),total)
        self.assertEqual(int(stats['denominator_u64'][0]),den)

    def test_peroutput_RQ_units(self):
        a=np.asarray([[3,-5,11],[-3,5,-11]],np.int32);d=np.asarray([1,2],np.int16)
        m=np.asarray([1<<30]*3,np.int32);e=np.asarray([0,1,-1],np.int16)
        out,p=g.requant(a,d,m,e,Counter())
        expected=[[round(Fraction(int(a[i,j])*int(m[j]),1)*Fraction(2)**(int(e[j])+int(d[i])-31)) for j in range(3)] for i in range(2)]
        np.testing.assert_array_equal(out,expected)

    def test_exact_tie_router_Q15_sum(self):
        lut=np.rint(np.exp2(-np.arange(2049,dtype=np.float64)/128)*(1<<24)).astype(np.uint32)
        c={'L0.router_w8':np.zeros((40,4),np.int8),'L0.router_exp8':np.zeros(40,np.int16),'route_exp2_q24':lut}
        result,counts=g.router(np.ones((1,4),np.int32),c,0,8,Counter())
        np.testing.assert_array_equal(result['ids'],[np.arange(8)])
        np.testing.assert_array_equal(result['gate_q15'],np.full((1,8),4096))
        self.assertEqual(int(result['gate_q15'].sum()),32768)

    def test_SiLU_boundaries_are_counted(self):
        grid=np.arange(-8192,8193,dtype=np.float64)/256
        lut=g.fp_encode(grid*np.exp(-np.logaddexp(0,-grid)),12)
        counts=Counter();x=np.asarray([-(32<<12)-1,-(32<<12),0,32<<12,(32<<12)+1],np.int32)
        out,index=g.silu(x,lut,Counter(),counts)
        self.assertEqual(int(out[0]),0);self.assertEqual(int(out[-1]),int(x[-1]));self.assertEqual(int(out[2]),0)
        self.assertEqual(counts['silu_negative_asymptote'],1);self.assertEqual(counts['silu_positive_identity'],1)
        np.testing.assert_array_equal(index,[0,0,8192,16384,16384])

    def test_no_silent_overflow(self):
        with self.assertRaises(OverflowError):g.cast32([1<<31])
        with self.assertRaises(OverflowError):g.shift([1<<62],-2)
        with self.assertRaises(OverflowError):g.add([1<<62],[1<<62])

if __name__=='__main__':unittest.main()
