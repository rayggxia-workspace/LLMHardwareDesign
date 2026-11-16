import unittest
import numpy as np
from stream_addresses import Addresses


class AddressTests(unittest.TestCase):
    def test_indexed_gather_addresses_and_negative_ids(self):
        m={'values':{'table':{'shape':[7,3]},'ids':{'shape':[2,2]},'out':{'shape':[2,2,3]}},'tasks':[]}
        a=Addresses(m,{'table':{'address_words':50},'ids':{'address_words':0},'out':{'address_words':100}})
        t={'inputs':['table','ids'],'outputs':['out'],'attributes':{'axis':0}}
        ids=np.array([[0,-1],[2,4]],dtype=np.int64)
        expected=np.take(np.arange(21).reshape(7,3)+50,ids,axis=0).reshape(-1)
        for i,n in enumerate(expected):self.assertEqual(a.gather(t,i,ids),(n,i//3))
        with self.assertRaises(ValueError):a.gather(t,0,np.array([[7,0],[0,0]]))

    def test_transposed_runtime_b_and_batched_broadcast(self):
        m={'values':{'a':{'shape':[2,3,4]},'b':{'shape':[1,5,4]},'bt':{'shape':[1,4,5]},'o':{'shape':[2,3,5]}},
           'tasks':[{'op':'Transpose','inputs':['b'],'outputs':['bt'],'attributes':{'perm':[0,2,1]}}]}
        a=Addresses(m,{'a':{'address_words':0},'b':{'address_words':24},'bt':{'address_words':100},'o':{'address_words':200}})
        left=np.arange(24).reshape(2,3,4);right=np.arange(20).reshape(1,5,4)+24
        t={'inputs':['a','bt'],'outputs':['o']}
        for o in range(30):
            batch,row,col=np.unravel_index(o,(2,3,5))
            for k in range(4):self.assertEqual(a.dot(t,o,k),(left[batch,row,k],right[0,col,k]))
        with self.assertRaises(ValueError):a.dot(t,30,0)
        with self.assertRaises(ValueError):a.dot(t,0,4)


if __name__=='__main__':unittest.main()
