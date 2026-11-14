import unittest

from benchmark_tile_handoff_dp import compare, problem
from event_lowering import lower
from event_tiling import lower_tiles
from run import compile_event_graph
from solver import Unsupported


class TileHandoffTest(unittest.TestCase):
    def test_three_operator_pairs_generate_tile_level_waits_and_control(self):
        for case in ('matmul-softmax', 'matmul-relu', 'add-rmsnorm'):
            with self.subTest(case=case):
                model, hardware = problem(3, 2, 16, case)
                lowered, _ = lower(model, hardware)
                tasks = {row['id']: row for row in lowered['tasks']}
                self.assertEqual(tasks['produce::tile::1:2']['after'], ['produce::tile::0:1'])
                self.assertEqual(tasks['consume::tile::0:1']['after'], ['produce::tile::0:1'])
                self.assertEqual(tasks['consume::tile::1:2']['after'],
                                 ['consume::tile::0:1', 'produce::tile::1:2'])
                self.assertEqual(tasks['y::tile_join']['after'],
                                 [f'consume::tile::{i}:{i + 1}' for i in range(3)])
                result = compile_event_graph(model, hardware, emit_dependencies=True)
                self.assertEqual(result['status'], 'planned')
                self.assertTrue(result['verification']['passed'])
                self.assertFalse(result['phase_dependencies']['completion_only_blockers'])
                commands = result['outputs']['program']['mother'][:-1]
                by_task = {row['task_id']: row for row in commands}
                self.assertEqual(by_task['consume::tile::0:1']['wait_for'],
                                 [by_task['produce::tile::0:1']['sequence']])
                self.assertEqual([node['id'] for node in model['tasks']], ['produce', 'consume'])

    def test_fanout_and_group_boundary(self):
        model, hardware = problem(3, 2, 16)
        model['tasks'].extend([
            {'id': 'consume2', 'op': 'Relu', 'inputs': ['x'], 'outputs': ['z']},
            {'id': 'outside', 'op': 'Identity', 'inputs': ['x'], 'outputs': ['w']},
        ])
        model['values']['z'] = model['values']['w'] = model['values']['x']
        model['outputs'].append('z')
        group = hardware['event_model']['tile_groups'][0]
        group['nodes'].append('consume2')
        group['axes']['z'] = 0
        rewritten, _, _ = lower_tiles(model, [group])
        nodes = {node['id']: node for node in rewritten['tasks']}
        self.assertEqual(nodes['consume::tile::1:2']['inputs'], ['x::tile::1:2'])
        self.assertEqual(nodes['consume2::tile::1:2']['inputs'], ['x::tile::1:2'])
        self.assertEqual(nodes['outside']['inputs'], ['x'])
        self.assertEqual(nodes['x::tile_join']['outputs'], ['x'])

    def test_declines_unqualified_axis_and_malformed_groups(self):
        model, hardware = problem(3, 2, 16)
        model['tasks'][1]['attributes']['axis'] = 0
        result = compile_event_graph(model, hardware)
        self.assertEqual(result['status'], 'blocked_lowering')
        self.assertNotIn('outputs', result)
        group = hardware['event_model']['tile_groups'][0]
        with self.assertRaisesRegex(Unsupported, 'invalid or overlapping'):
            lower_tiles(model, [group, group])

    def test_handoff_reduces_time_with_equal_work(self):
        barrier = compare(4, 4, 8, 16, True)
        handoff = compare(4, 4, 8, 16, False)
        self.assertEqual((barrier['ticks'], handoff['ticks']), (56, 41))
        self.assertEqual((barrier['intermediate_peak_tiles'], handoff['intermediate_peak_tiles']), (4, 2))
        self.assertEqual(barrier['dispatches'], handoff['dispatches'])
        self.assertEqual(handoff['ddr_bytes'], 0)
        self.assertGreater(handoff['peak_bucket_states'], barrier['peak_bucket_states'])

    def test_two_windows_require_interleaving(self):
        barrier = compare(4, 2, 8, 16, True)
        handoff = compare(4, 2, 8, 16, False)
        self.assertEqual(barrier['status'], 'no_plan_in_bounded_search')
        self.assertEqual(handoff['status'], 'planned')
        self.assertEqual(handoff['intermediate_peak_tiles'], 2)
