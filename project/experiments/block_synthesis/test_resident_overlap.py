from copy import deepcopy
import random
import unittest

from resident_overlap import binding_channels,build,digest,first_gap,search
from resident_replay import replay
from test_resident_records import e_graph
from test_native_reuse import timing
from verify_resident_overlap import verify


def fixture(dependent=False):
    g=e_graph([('a','b'),('n0','c') if dependent else ('c','d')],['n0','n1'])
    actors={name:{'kind':'E','site':name+'.S','words':2,'stride':1,'load_ticks':3,'store_ticks':5} for name in ('E0','E1')}
    events=[]
    for i,n in enumerate(g['operations']):
        actor='E'+str(i)
        for at,x in enumerate(n['inputs']):events.append({'op':'LOAD','actor':actor,'address':at,'record':x,
            'external_address':g['objects'][x]['external_address'],'wait_ack':True})
        events.append({'op':'E','actor':actor,'native':n['id'],'inputs':[0,1],'input_records':n['inputs'],
            'address':0,'record':n['output'],'opcode':5,'shift':0,'wait_s_ack':True})
        events.append({'op':'STORE','actor':actor,'address':0,'record':n['output'],
            'external_address':g['objects'][n['output']]['external_address'],'wait_ack':True})
    return g,{'status':'planned','actors':actors,'events':events,'zero_address':0,'service_timing':timing(),
              'copy_ticks':22,'native_service_ticks':40,'total_ticks':62,
              'external_load_words':4,'external_store_words':2,'external_words':6}


def cp_optimum(dag):
    """Independent arbitrary interval optimization, not actor-head search."""
    from ortools.sat.python import cp_model
    m=cp_model.CpModel();horizon=sum(n['duration'] for n in dag['nodes']);starts=[];ends=[];channels={}
    for n in dag['nodes']:
        i=n['event'];start=m.NewIntVar(0,horizon,'s'+str(i));end=m.NewIntVar(0,horizon,'e'+str(i))
        interval=m.NewIntervalVar(start,n['duration'],end,'i'+str(i));starts.append(start);ends.append(end)
        if n['channel'] is not None:channels.setdefault(n['channel'],[]).append(interval)
    for n in dag['nodes']:
        for d in n['deps']:m.Add(starts[n['event']]>=ends[d])
    for rows in channels.values():m.AddNoOverlap(rows)
    final=m.NewIntVar(0,horizon,'finish');m.AddMaxEquality(final,ends);m.Minimize(final)
    solver=cp_model.CpSolver();solver.parameters.num_search_workers=1
    if solver.Solve(m)!=cp_model.OPTIMAL:raise AssertionError('finite CP reference was not proven optimal')
    return solver.Value(final)


class TestResidentOverlap(unittest.TestCase):
    def test_long_shared_channel_history_is_iterative(self):
        nodes=[];streams={'A':[],'B':[]};length=900
        for i in range(2*length):
            actor='A' if i<length else 'B';stream=streams[actor]
            nodes.append({'event':i,'actor':actor,'duration':1,'channel':None if stream else 0,
                          'deps':[stream[-1]] if stream else []});stream.append(i)
        dag={'nodes':nodes,'streams':streams,'channel_by_actor':{'A':0,'B':0},'scope':'long trace unit fixture'}
        greedy=search(dag,width=1);bounded=search(dag,width=4,backbone=greedy)
        self.assertEqual(greedy['makespan'],length+1);self.assertEqual(bounded['makespan'],length+1)
        self.assertEqual(len(bounded['decisions']),2*length)
        self.assertEqual(sorted(r['event'] for r in bounded['decisions']),list(range(2*length)))

    def test_rebinding_requires_actual_qualified_store_and_io_contract(self):
        from resident_survey import build_actors
        from test_resident_bindings import fixture as declared_fixture
        ir,q=declared_fixture();actors=build_actors(ir,q);h=ir['hardware']
        p={'actors':actors,'service_timing':q};mapping={name:name for name in actors}
        channels=binding_channels(p,h,mapping)
        self.assertEqual(channels,{name:h['leaf_inventory'][name]['memory_group']%h['virtual_memory']['channels'] for name in actors})
        bad=deepcopy(h);bad['leaf_inventory']['matrix']['words']-=1
        with self.assertRaisesRegex(ValueError,'storage'):binding_channels(p,bad,mapping)
        bad=deepcopy(h);bad['leaf_inventory']['matrix']['io_write_ticks']+=50
        with self.assertRaisesRegex(ValueError,'descriptor'):binding_channels(p,bad,mapping)
        bad=deepcopy(h);bad['tile_service_bindings']['P']=[]
        with self.assertRaises((ValueError,IndexError)):binding_channels(p,bad,mapping)
        bad=deepcopy(h);bad['tile_service_bindings']['qualification_sha256']='forged'
        with self.assertRaisesRegex(ValueError,'qualified'):binding_channels(p,bad,mapping)

    def test_independent_streams_overlap_but_write_ack_dependency_does_not(self):
        for dependent,expected in ((False,31),(True,62)):
            g,p=fixture(dependent);values={(o['tensor'],0):7 for o in g['objects'].values() if o['kind']=='external'}
            self.assertTrue(replay(g,p,values)['passed'])
            mapping={'E0':0,'E1':1};dag=build(g,p,mapping)
            for width in (1,8,None):
                s=search(dag,width=width);self.assertEqual(s['makespan'],expected)
                self.assertTrue(verify(g,p,dag,s,mapping)['passed'])
            self.assertEqual(cp_optimum(dag),expected)

    def test_gap_filling_and_same_channel_exclusion(self):
        self.assertEqual(first_gap(((10,20),(30,40)),0,7),0)
        self.assertEqual(first_gap(((10,20),(30,40)),8,7),20)
        g,p=fixture();mapping={'E0':0,'E1':0};dag=build(g,p,mapping)
        exact=search(dag,width=None)
        self.assertEqual(exact['makespan'],cp_optimum(dag));self.assertGreater(exact['makespan'],31)
        self.assertTrue(verify(g,p,dag,exact,mapping)['passed'])

    def test_exact_search_against_finite_interval_reference_and_bounded_backbone(self):
        rng=random.Random(220191)
        for _ in range(24):
            # Durations vary independently of the product fixture, testing the
            # scheduling algorithm rather than making a performance claim.
            nodes=[];streams={name:[] for name in ('A','B')}
            for i in range(6):
                name='A' if i<3 else 'B';dep=[i-1] if i%3 else []
                if i>=3 and rng.randrange(3)==0:dep.append(rng.randrange(3))
                nodes.append({'event':i,'actor':name,'duration':rng.randrange(1,6),
                    'channel':0 if rng.randrange(2) else None,'deps':sorted(set(dep))});streams[name].append(i)
            dag={'streams':streams,'nodes':nodes,'channel_by_actor':{'A':0,'B':0},'scope':'unit finite intervals'}
            exact=search(dag,width=None);self.assertEqual(exact['makespan'],cp_optimum(dag))
            greedy=search(dag,width=1);bounded=search(dag,width=4,backbone=greedy)
            self.assertLessEqual(bounded['makespan'],greedy['makespan'])
            self.assertGreaterEqual(bounded['makespan'],exact['makespan'])

    def test_live_frontier_keeps_long_range_fanout_across_three_actors(self):
        rng=random.Random(220195)
        for _ in range(24):
            nodes=[];streams={actor:[] for actor in ('A','B','C')}
            for i in range(9):
                actor=('A','B','C')[i//3];stream=streams[actor]
                deps=([stream[-1]] if stream else [])
                if i>=3:
                    deps.extend(rng.sample(range(3*(i//3)),rng.randrange(3)))
                nodes.append({'event':i,'actor':actor,'duration':rng.randrange(1,6),
                    'channel':None if rng.randrange(2) else (0 if actor in ('A','C') else 1),
                    'deps':sorted(set(deps))});stream.append(i)
            dag={'nodes':nodes,'streams':streams,'channel_by_actor':{'A':0,'B':1,'C':0},'scope':'three-actor fanout unit fixture'}
            optimum=cp_optimum(dag);exact=search(dag,width=None)
            self.assertEqual(exact['makespan'],optimum)
            greedy=search(dag,width=1);bounded=search(dag,width=2,backbone=greedy)
            self.assertGreaterEqual(bounded['makespan'],optimum);self.assertLessEqual(bounded['makespan'],greedy['makespan'])

    def test_forged_mapping_time_actor_order_and_external_ack_are_rejected(self):
        g,p=fixture(True);mapping={'E0':0,'E1':1};dag=build(g,p,mapping);s=search(dag,width=8)
        bad=deepcopy(s);bad['decisions'][0]['end']-=1
        with self.assertRaises(ValueError):verify(g,p,dag,bad,mapping)
        with self.assertRaisesRegex(ValueError,'binding'):verify(g,p,dag,s,{'E0':0,'E1':0})
        bad=deepcopy(s);row=next(r for r in bad['decisions'] if r['event']==4);row['start']=0;row['end']=3
        with self.assertRaisesRegex(ValueError,'hazard'):verify(g,p,dag,bad,mapping)
        bad=deepcopy(s);bad['decisions'].pop()
        with self.assertRaisesRegex(ValueError,'coverage'):verify(g,p,dag,bad,mapping)
        forged=deepcopy(dag);forged['nodes'][4]['deps']=[]
        bad=deepcopy(s);bad['dag_sha256']=digest(forged)
        with self.assertRaisesRegex(ValueError,'dependency'):verify(g,p,forged,bad,mapping)
        forged=deepcopy(dag);forged['streams']['E0'].pop()
        bad=deepcopy(s);bad['dag_sha256']=digest(forged)
        with self.assertRaisesRegex(ValueError,'stream coverage'):verify(g,p,forged,bad,mapping)

    def test_external_war_waw_edges_survive_shared_scratch_addresses(self):
        g,p=fixture();p=deepcopy(p)
        # Trace-level hazard fixture only: these deliberate aliases are not a
        # source-qualified pointwise program or a numeric hardware claim.
        p['events'][7]['external_address']=p['events'][0]['external_address']
        dag=build(g,p,{'E0':0,'E1':1})
        self.assertIn(0,dag['nodes'][7]['deps'])
        p['events'][4]['external_address']=p['events'][3]['external_address']
        p['events'][7]['external_address']=p['events'][3]['external_address']
        dag=build(g,p,{'E0':0,'E1':1})
        self.assertIn(3,dag['nodes'][4]['deps']);self.assertIn(4,dag['nodes'][7]['deps']);self.assertIn(3,dag['nodes'][7]['deps'])


if __name__=='__main__':unittest.main()
