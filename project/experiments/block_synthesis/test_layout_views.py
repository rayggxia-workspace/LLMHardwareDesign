import unittest
import numpy as np
from layout_views import view, broadcast_index
from leaf_lowering import lower
from solver import Unsupported
from test_leaf_lowering import fixture


class TestLayoutViews(unittest.TestCase):
    def test_transpose_concat_and_negative_slice_match_numpy(self):
        arrays={'x':np.arange(24).reshape(2,3,4)}
        cases=[('Transpose',['x'],{'perm':[2,0,1]},arrays['x'].transpose(2,0,1)),
               ('Slice',['x','starts','ends','axes','steps'],{},arrays['x'][:,:,::-1])]
        for op,ins,attrs,expected in cases:
            values={'x':{'shape':[2,3,4]},'y':{'shape':list(expected.shape)},
                    'starts':{'constant':[-1]},'ends':{'constant':[-999]},
                    'axes':{'constant':[2]},'steps':{'constant':[-1]}}
            fn=view({'op':op,'inputs':ins,'outputs':['y'],'attributes':attrs},values)
            actual=[arrays[n].reshape(-1)[j] for n,j in map(fn,range(expected.size))]
            np.testing.assert_array_equal(np.array(actual).reshape(expected.shape),expected)
        values={'a':{'shape':[2,1]},'b':{'shape':[2,2]},'y':{'shape':[2,3]}}
        fn=view({'op':'Concat','inputs':['a','b'],'outputs':['y'],'attributes':{'axis':1}},values)
        self.assertEqual([fn(i) for i in range(6)],[('a',0),('b',0),('b',1),('a',1),('b',2),('b',3)])

    def test_broadcast_is_address_reuse(self):
        x=np.arange(3).reshape(1,3)
        actual=[x.reshape(-1)[broadcast_index(i,[2,4,3],[1,3])] for i in range(24)]
        np.testing.assert_array_equal(np.array(actual).reshape(2,4,3),np.broadcast_to(x,(2,4,3)))
        with self.assertRaises(Unsupported):broadcast_index(0,[2,4],[3])

    def test_scalar_record_transpose_aliases_and_output_order_is_explicit(self):
        f={'bits':16,'exponent':-10,'lanes':1}
        m={'tasks':[{'id':'t','op':'Transpose','inputs':['x'],'outputs':['y'],'attributes':{'perm':[1,0]}}],
           'values':{'x':{'shape':[2,3],'format':f},'y':{'shape':[3,2],'format':f}},'outputs':['y']}
        graph,_=lower(m,fixture())
        self.assertEqual(graph['tasks'],[])
        self.assertEqual([graph['values'][r['value']]['offset_elements'] for r in graph['output_bindings']],[0,3,1,4,2,5])
        self.assertEqual(len(graph['address_views']),1)
        # Two-lane records cannot be transposed for free into a different pair.
        f['lanes']=2
        with self.assertRaisesRegex(Unsupported,'real record permutation'):lower(m,fixture())


if __name__=='__main__':unittest.main()
