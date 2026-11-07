import copy
import unittest
from evaluate import hardware
from search import compile_graph, earliest, memory_ok, Unsupported, verify


def graph():
    return {'tasks':[
        {'id':'a','op':'MatMul','inputs':['x'],'outputs':['a'],'dependencies':[], 'work':40000,'dtype':'FLOAT'},
        {'id':'b','op':'MatMul','inputs':['x'],'outputs':['b'],'dependencies':[], 'work':40000,'dtype':'FLOAT'},
        {'id':'c','op':'Mul','inputs':['a','b'],'outputs':['c'],'dependencies':['a','b'], 'work':16,'dtype':'FLOAT'}],
        'sizes':{'x':16,'a':16,'b':16,'c':16}, 'inputs':['x'],'outputs':['c'],'weights':[]}


class Tests(unittest.TestCase):
    def test_resource_slot(self):
        self.assertEqual(earliest({'r':[(10,20)]},['r'],0,4),0)
        self.assertEqual(earliest({'r':[(10,20)]},['r'],8,4),20)

    def test_temporal_capacity(self):
        a={'a':{'start':0,'end':10,'bytes':16},'b':{'start':10,'end':20,'bytes':16}}
        self.assertEqual(memory_ok(a,16),(True,16))
        a['b']['start']=9
        self.assertEqual(memory_ok(a,16),(False,32))

    def test_schedule_and_mutation(self):
        g=graph(); h=hardware(4096,['MatMul','Mul'])
        p=compile_graph(g,h,8,allow_estimates=True)
        self.assertEqual(p['status'],'analytical_plan')
        q=copy.deepcopy(p)
        q['schedule'][-1]['start']=0
        with self.assertRaises(AssertionError):verify(q,g,h)
        q=copy.deepcopy(p); q['static_links']=[]
        with self.assertRaises(AssertionError):verify(q,g,h)

    def test_configuration_changes(self):
        g=graph(); h=hardware(1,['MatMul','Mul'])
        self.assertEqual(compile_graph(g,h,4,allow_estimates=True)['status'],'search_exhausted')
        h=hardware(4096,['MatMul','Mul'])
        h['services']=[s for s in h['services'] if s['instance'] in ('P1','J1')]
        p=compile_graph(g,h,4,allow_estimates=True)
        self.assertTrue(all(c['instance'] in ('P1','J1') for c in p['schedule']))
        h['links']=[e for e in h['links'] if e['src']=='MEM']
        self.assertEqual(compile_graph(g,h,4,allow_estimates=True)['status'],'search_exhausted')

    def test_no_implicit_fallback(self):
        g=graph(); h=hardware(4096,[])
        with self.assertRaises(Unsupported):compile_graph(g,h)
        g['tasks'][0]['op']='unregistered'
        with self.assertRaises(Unsupported):compile_graph(g,h,allow_estimates=True)

    def test_cross_layer_union_and_source_lease(self):
        g=graph(); h=hardware(4096,['MatMul','Mul'])
        # Force two producers into P0 and their consumer into J0.
        h['services']=[s for s in h['services'] if s['instance'] in ('P0','J0')]
        g['tasks'].append({'id':'d','op':'Mul','inputs':['a','c'],'outputs':['d'],
                           'dependencies':['a','c'],'work':8,'dtype':'FLOAT'})
        g['sizes']['d']=16; g['outputs']=['d']
        p=compile_graph(g,h,4,allow_estimates=True)
        self.assertEqual(p['static_links'].count('P0->J0'),1)
        copies=[t for c in p['schedule'] for t in c['transfers'] if t['tensor']=='a']
        self.assertEqual(p['memory']['P0']['a']['end'],max(t['end'] for t in copies))
        q=copy.deepcopy(p); q['memory']['P0']['a']['end']=0
        # Independent verifier must reject premature object release.
        with self.assertRaises(AssertionError):verify(q,g,h)


if __name__=='__main__':unittest.main()
