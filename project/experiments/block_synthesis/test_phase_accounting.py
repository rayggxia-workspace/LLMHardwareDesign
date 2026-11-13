from copy import deepcopy
import unittest
from unittest.mock import patch

from loop_dp import search
from phase_accounting import account, service_parts
from test_column_shards import fixture, compound


class TestPhaseAccounting(unittest.TestCase):
    def test_original_and_compound_costs_conserve_every_tick(self):
        for dynamic in (False, True):
            ir = fixture(columns=9)
            if dynamic:
                b = next(b for t in ir['tasks'] for b in t['bindings'] if 'frontier_partition' in b)
            else:
                b = compound(ir)
            next(t for t in ir['tasks'] if t['id'] == 'v')['bindings'] = [b]
            plan = search(ir['tasks'], ir['hardware'], width=4)
            with patch('verify_primitive_cost.duration', return_value=1):
                report = account(ir, plan)
            self.assertTrue(report['passed'])
            serial = report['serial_components']
            self.assertGreater(serial['core_ticks'], 0)
            self.assertGreater(serial['local_S_ticks'], 0)
            self.assertGreater(serial['descriptor_ticks'], 0)
            self.assertLessEqual(report['descriptor_pool_demand_lower_bound'], plan['makespan'])
            for channel in report['channels'].values():
                self.assertGreater(channel['reserved_without_descriptor_ticks'], 0)

    def test_selected_duration_and_cached_reads_cannot_be_forged(self):
        ir = fixture()
        plan = search(ir['tasks'], ir['hardware'])
        task = next(t for t in ir['tasks'] if t['id'] == plan['tasks'][0]['id'])
        row = plan['tasks'][0]
        binding = next(b for b in task['bindings'] if b['id'] == row['binding'])
        work = next(p for p in ir['program'] if p['id'] == row['id'])['primitive_counts']
        bad = deepcopy(row)
        bad['end'] += 1
        with self.assertRaisesRegex(ValueError, 'reproduce service'):
            service_parts(work, binding, bad, ir['hardware'])


if __name__ == '__main__':
    unittest.main()
