import unittest
from loop_dp import search
from search_diagnostics import bounds,minimum_resource_time


class TestSearchDiagnostics(unittest.TestCase):
    def test_mandatory_resource_proves_no_remaining_ordering_gain(self):
        h={'sites':{'S':{'words':8}},'resources':{'r':1},'nets':{}}
        tasks=[{'id':str(i),'bindings':[{'id':'b','site':'S','ticks':ticks,'resources':['r'],
            'nets':[],'scratch_words':1,'external_read_words':0,'external_write_words':0}]}
            for i,ticks in enumerate([3,7,11])]
        p=search(tasks,h);r=bounds(tasks,h,p)
        self.assertEqual(r['completion_lower_bound'],21)
        self.assertEqual(r['maximum_time_reduction_fraction_with_current_actions'],0)

    def test_alternatives_do_not_create_a_false_mandatory_resource(self):
        h={'sites':{'S':{'words':8}},'resources':{'r':1,'q':1},'nets':{}}
        tasks=[{'id':str(i),'bindings':[{'id':r,'site':'S','ticks':5,'resources':[r],
            'nets':[],'scratch_words':1,'external_read_words':0,'external_write_words':0} for r in ['r','q']]}
            for i in range(2)]
        p=search(tasks,h,width=8);r=bounds(tasks,h,p)
        self.assertEqual(r['mandatory_resource_bounds'],{})
        self.assertEqual(r['completion_lower_bound'],5)
        self.assertEqual(p['makespan'],5)

    def test_equivalent_pool_counts_alternative_instance_occupancy(self):
        h={'sites':{'S':{'words':8}},'resources':{'r':1,'q':1},'nets':{},
           'resource_pools':{'compute':['r','q']}}
        tasks=[{'id':str(i),'bindings':[{'id':r,'site':'S','ticks':5,'resources':[r],
            'nets':[],'scratch_words':1,'external_read_words':0,'external_write_words':0} for r in ['r','q']]}
            for i in range(3)]
        p=search(tasks,h,width=64);r=bounds(tasks,h,p)
        self.assertEqual(r['mandatory_resource_bounds'],{})
        self.assertEqual(r['resource_pool_bounds']['compute']['minimum_resource_time'],15)
        self.assertEqual(r['completion_lower_bound'],8)
        self.assertEqual(p['makespan'],10)

    def test_materialized_auxiliary_work_is_phase_length_not_service_length(self):
        from test_materialized_tiles import TestMaterializedTiles
        ir=TestMaterializedTiles().fixture(columns=11)
        task=next(t for t in ir['tasks'] if any('materialized_tile' in b for b in t['bindings']))
        b=next(b for b in task['bindings'] if 'materialized_tile' in b)
        offsets=b['materialized_tile']['resource_offsets'];aux=set(offsets)
        expected=sum(hi-lo for lo,hi in offsets.values())
        self.assertLess(expected,b['ticks']*len(aux))
        self.assertEqual(minimum_resource_time(b,aux),expected)
        primary=set(b['resources'])-aux
        self.assertEqual(minimum_resource_time(b,primary),b['ticks']*len(primary))
        # The certified per-resource bound must also use that short phase.
        selected={**task,'after':[],'bindings':[b]}
        p=search([selected],ir['hardware'],width=8)
        r=bounds([selected],ir['hardware'],p)
        self.assertEqual(r['completion_lower_bound'],p['makespan'])
        for resource,(lo,hi) in offsets.items():
            self.assertEqual(r['mandatory_resource_bounds'][resource]['minimum_reserved_work'],hi-lo)


if __name__=='__main__':unittest.main()
