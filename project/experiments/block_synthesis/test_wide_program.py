import unittest
import numpy as np
from full_integer import Q
from wide_program import Builder,Value,execute
from streaming_ir import primitive_body,counts


class WideProgramTests(unittest.TestCase):
    def test_emitted_shift_drives_replay(self):
        b=Builder();x=Value('x',(4,),0);y=b.mul(x,b.constant(3),1)
        p={'instructions':b.nodes,'outputs':{'out':y.name}}
        actual=execute(p,{'x':Q(np.array([-3,-1,1,3]),0)},[[1,2]],None)['out'].raw
        self.assertEqual(actual.tolist(),[-4,-2,2,4])
        b.nodes[-1]['attributes']['shift']=0
        changed=execute(p,{'x':Q(np.array([-3,-1,1,3]),0)},[[1,2]],None)['out'].raw
        self.assertEqual(changed.tolist(),[-9,-3,3,9])

    def test_full_s32_three_part_identity(self):
        x=np.array([-(1<<31),-(1<<31)+1,-32768,-1,0,32767,32768,(1<<31)-2,(1<<31)-1],dtype=np.int64)
        low=(x&65535).astype(np.uint16).view(np.int16).astype(np.int64)
        high=x>>16;flag=(low<0).astype(np.int64)
        np.testing.assert_array_equal(low+(high+flag)*65536,x)
        self.assertTrue(np.all((-32768<=high)&(high<=32767)))

    def test_mask_is_real_dataflow_not_negative_infinity_arithmetic(self):
        b=Builder();b.current='soft';x=Value('x',(2,2),0)
        floor=b.emit('MaskFloor',[x],x.shape,0,floor=-(1<<31));maximum=b.reduce('Max',floor)
        centered=b.add([x,maximum],[1,-1]);zero=b.emit('MaskZero',[centered],centered.shape,0,clear=True)
        p={'instructions':b.nodes,'outputs':{'out':zero.name}}
        result=execute(p,{'x':Q(np.array([[10,100],[4,8]]),0,np.array([[True,False],[True,True]]))},[[1,2]],None)['out']
        self.assertEqual(result.raw.tolist(),[[0,0],[-4,0]])
        self.assertIsNone(result.mask)

    def test_unregistered_primitive_is_rejected(self):
        with self.assertRaises(ValueError):primitive_body({'op':'CPUFallback','shape':[1],'attributes':{}})
        with self.assertRaises(ValueError):execute({'instructions':[{'id':'x','op':'CPUFallback','inputs':[],
            'shape':[1],'exponent':0,'bits':32,'attributes':{}}],'outputs':{}},{},[[1,2]],None)


if __name__=='__main__':unittest.main()
