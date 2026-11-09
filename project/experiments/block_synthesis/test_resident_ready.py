from copy import deepcopy
import unittest

from resident_batch import plan
from resident_ready import ReadyGraph
from test_resident_batch import case
from verify_resident_batch import replay
from native_pointwise import execute


class TestResidentReady(unittest.TestCase):
    def test_actual_dependencies_and_B_identity_control_actions(self):
        _,tile,_,_,_=case();dag=ReadyGraph(tile,3);done=frozenset()
        for _ in range(len(dag.nodes)):
            actions=dag.actions(done,policy='all')
            self.assertTrue(actions)
            for members in actions:
                for name in members:self.assertTrue(dag.dependencies[name]<=done)
                if len(members)>1:self.assertEqual(len({dag.signatures[n] for n in members}),1)
            done|=frozenset(actions[0])
        self.assertEqual(done,set(dag.nodes));self.assertEqual(dag.actions(done),[])
        _,tile,_,_,_=case(simple=True,dependent_b=True)
        self.assertTrue(all(len(a)==1 for a in ReadyGraph(tile,3).actions(frozenset(),policy='all')))

    def test_exhaustive_small_family_is_rank_independent_and_checked(self):
        _,tile,actors,q,scalar=case(simple=True)
        values={('x',0):-32768,('x',1):32767,('y',0):3,('y',1):4}
        candidates=[plan(tile,actors,0,q,scalar,width=None,schedule='ready',grouping_policy='all',rank_policy=rank)
                    for rank in ('copy_cost','future_copies','future_layout')]
        self.assertEqual(len({p['total_ticks'] for p in candidates}),1)
        fixed=plan(tile,actors,0,q,scalar,width=None)
        self.assertLessEqual(candidates[0]['total_ticks'],fixed['total_ticks'])
        for p in candidates:self.assertTrue(replay(tile,p,values)['passed'])
        greedy=plan(tile,actors,0,q,scalar,width=1,schedule='ready',grouping_policy='all')
        self.assertEqual(greedy['search_method'],'strict_greedy')
        self.assertGreaterEqual(greedy['total_ticks'],candidates[0]['total_ticks'])

    def test_general_S32_DAG_uses_finite_memory_and_preserves_native_outputs(self):
        _,tile,actors,q,scalar=case()
        candidates=[plan(tile,actors,1000,q,scalar,width=width,schedule='ready',allow_batch=batch)
                    for width,batch in ((1,False),(1,True),(2,True))]
        for trial,edge in enumerate((-2147483648,0,2147483647)):
            values={('x',i):edge for i in range(3)}|{('y',i):(-32769,32768,-1)[i] for i in range(3)}|{('one',0):1}
            for p in candidates:
                result=replay(tile,p,values);self.assertTrue(result['passed'])
                for row,g in enumerate(tile['graphs']):
                    expected=execute(g,values)
                    for primitive,record in g['primitive_outputs'].items():
                        key=tile['graph']['primitive_outputs'][f'{row}:{primitive}']
                        self.assertEqual(result['observed_native_outputs'][key],expected[record])
                self.assertEqual(p['copy_ticks'],3*p['external_load_words']+5*p['external_store_words'])

    def test_checker_rejects_execution_before_real_dependency(self):
        _,tile,actors,q,scalar=case();p=plan(tile,actors,1000,q,scalar,width=1,schedule='ready')
        bad=deepcopy(p);at=next(i for i,e in enumerate(bad['events']) if e['op']=='E')
        bad['events'].insert(0,bad['events'].pop(at))
        values={('x',i):1 for i in range(3)}|{('y',i):2 for i in range(3)}|{('one',0):1}
        with self.assertRaises(ValueError):replay(tile,bad,values)


if __name__=='__main__':unittest.main()
