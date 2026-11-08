import unittest
from loop_dp import search
from search_diagnostics import bounds


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


if __name__=='__main__':unittest.main()
