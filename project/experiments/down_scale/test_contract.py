import copy
from fractions import Fraction
import unittest
import numpy as np
from numeric import check, shift_rne, encode_source, exponent_integer, calculate
from service import packet_bytes, build
from audit import trace_check
from replay import packets,receive


class Contract(unittest.TestCase):
    def test_signed_ties_and_extremes(self):
        for value in [-2**31,-129,-127,-5,-3,-1,0,1,3,5,127,129,2**31-1]:
            for shift in [0,1,2,7,31,63]:self.assertEqual(shift_rne(value,shift),round(Fraction(value,2**shift)))

    def test_symmetric_clip_zero_scale(self):
        x=np.array([-2**31,-129,-128,-127,0,127,128,2**31-1],dtype=np.int64)
        code,n=encode_source(x,-20)
        self.assertEqual(code.tolist(),[-127,-127,-127,-127,0,127,127,127]);self.assertEqual(n,5)
        self.assertEqual(exponent_integer(np.zeros(128,dtype=np.int32)),-20)
        self.assertEqual(exponent_integer(np.array([127,128],dtype=np.int32)),-19)

    def test_mixed_scale_raw_sum_invalid(self):
        qa=np.array([[1,1]],dtype=np.int8);qw=np.array([[3,3]],dtype=np.int8)
        result,stats=calculate(qa,qw,np.array([[0,1]],dtype=np.int8),np.array([[0]],dtype=np.int8),np.array([0],dtype=np.int8),1,2)
        self.assertEqual(result['acc'][0,0],9);self.assertEqual(result['out'][0,0],9)
        self.assertNotEqual(result['out'][0,0],int((qa.astype(np.int32)@qw.astype(np.int32).T)[0,0]))

    def test_early_rounding_differs(self):
        self.assertEqual(shift_rne(1,1)+shift_rne(1,1),0);self.assertEqual(shift_rne(2,1),1)

    def test_overflow_and_shift_rejection(self):
        for value in [2**31,-2**31-1]:
            with self.assertRaises(OverflowError):check(value,32)
        with self.assertRaises(OverflowError):check(2**63,64)
        with self.assertRaises(ValueError):shift_rne(1,64)
        with self.assertRaises(OverflowError):calculate(np.ones((1,2),dtype=np.int8),np.ones((1,2),dtype=np.int8),
            np.array([[0,63]],dtype=np.int8),np.array([[0]],dtype=np.int8),np.array([0],dtype=np.int8),1,2)

    def test_packet_quantum_and_batching(self):
        self.assertEqual(packet_bytes(16),packet_bytes(64));self.assertEqual(packet_bytes(64),128)
        self.assertEqual(packet_bytes(256),320);self.assertEqual(packet_bytes(2048),2176)
        raw=bytes(range(256))*10;p=packets(raw,1,7)
        self.assertEqual(receive(p,1,7,len(raw)),raw)
        for bad in [p[:-1],list(reversed(p)),[p[0][:-1]]]:
            with self.assertRaises(ValueError):receive(bad,1,7,len(raw))
        changed=bytearray(p[0]);changed[64]^=1
        with self.assertRaises(ValueError):receive([bytes(changed),*p[1:]],1,7,len(raw))

    def test_service_capacity_and_dependency_negative(self):
        pr={'name':'test','ag':128,'wg':8192,'mode':'dynamic'}
        g,s=build(pr,4,'near',2,4);result=g.schedule('critical')
        w={'nodes':g.nodes,'sizes':g.sizes,'packets':g.packets,'scheduled':result}
        self.assertGreater(trace_check(w),0);self.assertEqual(s['partial_staging_bytes'],1024)
        bad=copy.deepcopy(w);i=next(n['id'] for n in bad['nodes'] if n['duration'] and any(result['trace'][d][1]>0 for d in n['deps']))
        bad['scheduled']['trace'][i]=[0,bad['nodes'][i]['duration']]
        with self.assertRaises(AssertionError):trace_check(bad)
        with self.assertRaises(ValueError):build(pr,8,'near',2,4)


if __name__=='__main__':unittest.main()
