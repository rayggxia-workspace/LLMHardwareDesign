"""Algorithm invariants only. Native profiles are tested by the server replay."""
from copy import deepcopy
import unittest

from memory import profile_from_source, descriptor_ticks, attach_virtual_memory
from lowering import lower_rows
from run import compile_model
from test_solver import fixture
from verify import verify, InvalidPlan


# Minimal syntax fixture for parser drift checking; not measured bandwidth.
SOURCE = '''struct Config{int channels=2,credits=4,queue=32,period=6,phase=1,latency=20,seed=181;};
now%10==0; (r.address/64)%4; r.address/1024; bank.free=command+2;
bank.row==row?0:6; m.busfree=mems+4;'''


def virtual_fixture():
    g, h = fixture(words=4)
    h['routes'] = {}
    h['nets'] = {}
    h['virtual_memory'] = profile_from_source(SOURCE)
    for index, (site, meta) in enumerate(h['sites'].items()):
        port = site + '.io'
        meta.update(memory_group=index, io_resource=port, io_read_ticks=4, io_write_ticks=6)
        h['resources'][port] = 1
    return g, h


class TestVirtualMemory(unittest.TestCase):
    def test_zero_preconnections_needs_no_native_dma_or_pins(self):
        g, h = virtual_fixture()
        g['lowered'] = True
        result = compile_model(g, h, seconds=1, rounds=1)
        self.assertEqual(result['status'], 'planned', result)
        self.assertEqual(result['plan']['nets'], [])
        self.assertTrue(result['verification']['passed'])
        self.assertFalse(result['acceptance']['physical_routing_required'])
        self.assertFalse(result['acceptance']['native_dma_replay_required'])
        self.assertFalse(result['acceptance']['native_control_image_required'])
        self.assertTrue(result['outputs']['wiring']['interfaces'])
        self.assertFalse(result['outputs']['wiring']['all_pins_bound'])

    def test_credit_queue_and_latency_are_real_model_inputs(self):
        p = profile_from_source(SOURCE)
        base = descriptor_ticks(p, 64, 'load', 2)
        self.assertGreater(descriptor_ticks({**p, 'credits': 1}, 64, 'load', 2), base)
        self.assertGreater(descriptor_ticks({**p, 'queue': 1}, 64, 'load', 2), base)
        self.assertGreater(descriptor_ticks({**p, 'latency': 200}, 64, 'load', 2), base)
        self.assertGreater(descriptor_ticks(p, 128, 'store', 4), descriptor_ticks(p, 64, 'store', 4))

    def test_capacity_and_instance_rename_do_not_change_the_algorithm(self):
        g, h = virtual_fixture()
        h['sites']['new.sram'] = {**h['sites'].pop('right'), 'words': 2048}
        h['services']['right']['site'] = 'new.sram'
        g['lowered'] = True
        r = compile_model(g, h, seconds=1, rounds=0)
        self.assertEqual(r['status'], 'planned')
        self.assertEqual(r['resolved_hardware']['sites']['new.sram']['words'], 2048)

    def test_channel_claim_and_completion_are_independently_checked(self):
        g, h = virtual_fixture()
        h = attach_virtual_memory(g, h)
        from seed import serial_seed
        from solver import seed_bindings
        plan = serial_seed(g, h, seed_bindings(g, h))
        move = plan['moves'][0]
        channel = h['routes'][move['route']]['channel']
        self.assertTrue(any(c['resource'] == f'virtual-memory.channel.{channel}' for c in plan['claims']))
        bad = deepcopy(plan)
        bad['moves'][0]['end'] -= 1
        with self.assertRaises(InvalidPlan):
            verify(g, h, bad)

    def test_source_drift_and_invalid_configuration_are_rejected(self):
        with self.assertRaises(ValueError):
            profile_from_source(SOURCE.replace('bank.free=command+2', 'bank.free=command+99'))
        p = profile_from_source(SOURCE)
        with self.assertRaises(ValueError):
            descriptor_ticks({**p, 'credits': 0}, 1, 'load', 4)
        with self.assertRaises(ValueError):
            descriptor_ticks({**p, 'credits': 9}, 1, 'load', 4)

    def test_full_normalization_rows_preserve_shared_weights(self):
        _, h = fixture()
        h['services'] = {'n': {'op': 'RMSNorm', 'numeric': 'explicit-native-n', 'qualified': True,
            'row_replay': True, 'row_elements': 16, 'input_layouts': ['row', 'shared-row', 'scalar-word'],
            'input_words': [2, 2, 1], 'output_words': [2], 'site': 'left', 'ticks': 100, 'resources': []}}
        m = {'tasks': [{'id': 'n', 'op': 'RMSNorm', 'numeric': 'explicit-native-n',
                       'inputs': ['x', 'gamma', 'epsilon'], 'outputs': ['y']}],
             'values': {'x': {'shape': [3, 16]}, 'gamma': {'shape': [16]},
                        'epsilon': {'shape': []}, 'y': {'shape': [3, 16]}}, 'outputs': ['y']}
        g, = lower_rows(m, h)
        self.assertEqual(len(g['tasks']), 3)
        self.assertEqual(len([n for n in g['values'] if n.startswith('gamma')]), 1)
        self.assertEqual(len([n for n in g['values'] if n.startswith('epsilon')]), 1)
        self.assertTrue(all(len(t['inputs']) == 3 for t in g['tasks']))

    def test_compute_connections_are_required_even_when_there_is_no_copy(self):
        g, h = fixture()
        h['nets']['compute-only'] = {'cost': 7, 'fixed': False}
        for service in h['services'].values():
            service['nets'] = ['compute-only']
        from solver import Planner
        p = Planner(g, h).solve(seconds=2)
        self.assertIn('compute-only', p['nets'])
        verify(g, h, p)
        bad = deepcopy(p)
        bad['nets'].remove('compute-only')
        with self.assertRaises(InvalidPlan):
            verify(g, h, bad)
        self.assertNotIn('tasks', Planner(g, h, wire_budget=6).solve(seconds=2))

    def test_parallel_streams_overlap_compute_but_share_memory_channel(self):
        g, h = virtual_fixture()
        g['tasks'][1]['inputs'] = ['input']
        g['tasks'][1].pop('after', None)
        g['outputs'] = ['a.out', 'b.out']
        g['values']['a.out']['output_site'] = h['external']
        from parallel import parallel_seed
        from seed import serial_seed
        binding = {'a': 'left', 'b': 'right'}
        h = attach_virtual_memory(g, h)
        serial = serial_seed(g, h, binding)
        parallel = parallel_seed(g, h, binding)
        self.assertLess(parallel['makespan'], serial['makespan'])
        self.assertTrue(verify(g, h, parallel)['passed'])

    def test_compute_and_copy_static_driver_conflict_changes_binding(self):
        g, h = fixture()
        h['nets']['local-compute'] = {'cost': 1, 'fixed': False}
        for service in h['services'].values():
            service['nets'] = ['local-compute']
        h['incompatible_nets'] = [['local-compute', 'MEM>left']]
        from solver import optimize
        p = optimize(g, h, seconds=2, rounds=0)
        self.assertIn('tasks', p)
        self.assertNotIn('MEM>left', p['nets'])
        self.assertTrue(verify(g, h, p)['passed'])


if __name__ == '__main__':
    unittest.main()
