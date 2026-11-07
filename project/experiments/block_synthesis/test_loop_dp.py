from copy import deepcopy
import unittest
from loop_dp import optimize
from verify_loop_dp import verify


def binding(name,resource,ticks,nets=()):
    return {'id':name,'site':'S','resources':[resource],'ticks':ticks,'nets':list(nets),
            'scratch_words':2,'external_read_words':1,'external_write_words':1}


class TestLoopDP(unittest.TestCase):
    def test_frontier_explores_order_and_binding_and_improves_greedy(self):
        h={'resources':{'r0':1,'r1':1,'r2':1},'sites':{'S':{'words':8}},'nets':{}}
        tasks=[{'id':'A','bindings':[binding('a0','r0',3),binding('a1','r1',4)]},
               {'id':'B','bindings':[binding('b0','r0',3)]},
               {'id':'C','after':['A','B'],'bindings':[binding('c','r2',1)]}]
        result=optimize(tasks,h,width=4)
        self.assertEqual(result['baseline']['makespan'],7)
        self.assertEqual(result['makespan'],5)
        self.assertTrue(verify(tasks,h,result)['passed'])

    def test_static_net_history_survives_until_future_reuse(self):
        h={'resources':{'r0':1},'sites':{'S':{'words':8}},
           'nets':{'A':{'cost':1},'B':{'cost':2}}}
        tasks=[{'id':'first','bindings':[binding('a','r0',1,['A']),binding('b','r0',1,['B'])]},
               {'id':'later-layer','after':['first'],'bindings':[binding('c','r0',1,['B'])]}]
        result=optimize(tasks,h,width=2)
        self.assertEqual(result['wire_cost'],2)
        self.assertEqual(result['baseline']['wire_cost'],3)
        self.assertTrue(verify(tasks,h,result)['passed'])
        limited=optimize(tasks,h,width=2,wire_budget=2)
        self.assertEqual(limited['status'],'planned')
        self.assertNotEqual(limited['baseline']['status'],'planned')
        self.assertTrue(verify(tasks,h,limited,2)['passed'])

    def test_independent_checker_rejects_overlap_and_unknown_binding(self):
        h={'resources':{'r':1},'sites':{'S':{'words':8}},'nets':{}}
        tasks=[{'id':name,'bindings':[binding(name,'r',3)]} for name in ('A','B')]
        result=optimize(tasks,h,width=2);verify(tasks,h,result)
        bad=deepcopy(result);bad['tasks'][1]['start']=0;bad['tasks'][1]['end']=3
        with self.assertRaises(ValueError):verify(tasks,h,bad)
        bad=deepcopy(result);bad['tasks'][0]['binding']='invented'
        with self.assertRaises(ValueError):verify(tasks,h,bad)


if __name__=='__main__':unittest.main()
