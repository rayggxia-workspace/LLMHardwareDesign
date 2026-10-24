import unittest
from fractions import Fraction
import numpy as np
import falcon_int as f
import falcon_outproj as out

class OutProjection(unittest.TestCase):
    def fixture(self):
        rng=np.random.default_rng(72);x=rng.integers(-20000,20000,(3,16),dtype=np.int32);x[:,4:8]//=64;x[:,12:16]//=16
        w=rng.integers(-127,128,(5,16),dtype=np.int16).astype(np.int8);m=np.array([1<<30,(1<<30)+71,(1<<31)-1,(1<<30)+99,1<<30],np.int32);e=np.array([-3,-5,-8,0,-1],np.int16)
        return x,w,m,e
    def test_whole_row_exact_existing_int32_path(self):
        x,w,m,e=self.fixture();ops=f.Ops();got,alignment,width=out.grouped_linear(x,w,m,e,0,ops);y,a,d,acc=f.linear(x,w,m,e,f.Ops())
        for aa,bb in [(got['out_before_bias_q12'],y),(got['a8'],a),(got['a8_delta'][:,0],d),(got['partial_acc32'][:,0],acc)]:np.testing.assert_array_equal(aa,bb)
        self.assertEqual(width['groups'],1);self.assertNotIn('add_i64',ops.values);self.assertEqual(ops.values['matrix_int32_accum'],3*5*16)
    def test_group_complete_alignment_scalar_fraction(self):
        x,w,m,e=self.fixture();got,alignment,width=out.grouped_linear(x,w,m,e,4,f.Ops());g=4
        for t in range(3):
            for gi in range(g):
                raw=list(map(int,x[t,gi*4:(gi+1)*4]));d=0
                while max(abs(round(Fraction(v,1<<d))) for v in raw)>127:d+=1
                self.assertEqual(int(got['a8_delta'][t,gi]),d)
                expected=[round(Fraction(v,1<<d)) for v in raw];self.assertEqual(got['a8'][t,gi*4:(gi+1)*4].tolist(),expected)
            for o in range(5):
                unscaled=0
                for gi in range(g):
                    dot=sum(int(got['a8'][t,gi*4+j])*int(w[o,gi*4+j]) for j in range(4))
                    self.assertEqual(dot,int(got['partial_acc32'][t,gi,o]));unscaled+=dot*(1<<int(got['a8_delta'][t,gi]))
                scale=Fraction(int(m[o]),1<<31)*(Fraction(1<<int(e[o]),1) if e[o]>=0 else Fraction(1,1<<-int(e[o])))
                self.assertEqual(int(got['out_before_bias_q12'][t,o]),round(unscaled*scale))
                product=(int(got['rq_product_hi_i64'][t,o])<<64)|int(got['rq_product_lo_u64'][t,o]);self.assertEqual(product,int(got['aligned_sum_i64'][t,o])*int(m[o]))
        self.assertEqual(width['declared_rq_product_bits'],128);self.assertEqual(len(alignment),3*4)
    def test_i128_word_sign_and_guards(self):
        for n in (0,1,-1,(1<<80)+3,-(1<<80)-3,-(1<<127),(1<<127)-1):
            hi,lo=out.product_words(n);self.assertEqual((hi<<64)|lo,n)
        with self.assertRaises(OverflowError):out.product_words(1<<127)
        self.assertEqual(out.wide_rshift(-5,1),-2);self.assertEqual(out.wide_rshift(-7,1),-4)
    def test_group_constraints_and_storage(self):
        x,w,m,e=self.fixture()
        with self.assertRaises(ValueError):out.grouped_linear(x,w,m,e,3,f.Ops())
        with self.assertRaises(ValueError):out.grouped_linear(x,w.astype(np.int16),m,e,4,f.Ops())
        trace,_,_=out.grouped_linear(x,w,m,e,4,f.Ops());self.assertTrue(all(a.dtype.kind in 'iu' for a in trace.values()))
    def test_concrete_packet_accounting(self):
        self.assertEqual(out.wire_bytes(0),0);self.assertEqual(out.wire_bytes(1984),2016);self.assertEqual(out.wire_bytes(1985),2064);self.assertEqual(out.wire_bytes(10240),10432)
if __name__=='__main__':unittest.main()
