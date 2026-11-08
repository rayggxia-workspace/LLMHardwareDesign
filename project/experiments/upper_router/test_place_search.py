from copy import deepcopy
import unittest
from place_search import optimize
from test_resource_base import template


class PlacementTest(unittest.TestCase):
    def test_communication_changes_placement_without_mutating_source(self):
        library={'one':template()};original=deepcopy(library)
        instances={n:'one' for n in ('alpha','beta','gamma','omega')}
        nets=[{'driver':'alpha/out','sinks':['omega/in'],'weight':20}]
        positions,bounds,report=optimize(instances,library,nets,gap_dbu=20,alignment_dbu=1,rounds=3,width=4)
        self.assertLess(report['selected_wire_estimate_dbu'],report['initial_wire_estimate_dbu'])
        self.assertEqual(library,original)
        self.assertEqual(set(positions),set(instances))
        again=optimize(instances,library,nets,gap_dbu=20,alignment_dbu=1,rounds=3,width=4)
        self.assertEqual((positions,bounds,report),again)


if __name__=='__main__':unittest.main()
