"""Synthetic correctness fixtures; these are not hardware/model benchmarks."""
from copy import deepcopy
import unittest
from cover import propose_covers
from frontend import lower_elementwise
from solver import Unsupported, Planner, optimize
from test_solver import fixture
from verify import verify
from run import compile_model


class TestFrontend(unittest.TestCase):
    def test_registered_tiling_streams_external_tensor(self):
        g, h = fixture(words=3)
        h['services'] = {'left': {**h['services']['left'], 'elementwise': True, 'tile_elements': 8,
                                  'input_words': [2], 'output_words': [1], 'zero_pad_tail': True}}
        model = {'tasks': [{'id': 'a', 'op': 'add', 'numeric': 'test-int16', 'inputs': ['x'], 'outputs': ['y']}],
                 'values': {'x': {'shape': [127]}, 'y': {'shape': [127]}}, 'outputs': ['y']}
        tiled, = lower_elementwise(model, h)
        self.assertEqual(len(tiled['tasks']), 16)
        self.assertEqual(tiled['values']['x@120']['valid_elements'], 7)
        p = optimize(tiled, h, seconds=1, rounds=1)
        self.assertIn('tasks', p, p)
        self.assertLessEqual(verify(tiled, h, p)['peak_words']['left'], 3)
        self.assertEqual(p['external_words'], 48)

    def test_padding_not_silently_invented(self):
        _, h = fixture()
        h['services']['left'].update(elementwise=True, tile_elements=8, input_words=[1], output_words=[1])
        model = {'tasks': [{'id': 'a', 'op': 'add', 'numeric': 'test-int16', 'inputs': ['x'], 'outputs': ['y']}],
                 'values': {'x': {'shape': [9]}, 'y': {'shape': [9]}}, 'outputs': ['y']}
        with self.assertRaises(Unsupported):
            lower_elementwise(model, h)

    def test_chain_dp_keeps_separate_and_qualified_fusion(self):
        g, h = fixture()
        h['services']['pair'] = {**h['services']['left'], 'op': 'add_pair', 'ticks': 4,
            'pattern': ['add', 'add'], 'pattern_numeric': ['test-int16', 'test-int16'],
            'pattern_attributes': [{}, {}], 'pattern_inputs': [[0, 0]],
            'input_words': [2], 'output_words': [2]}
        covers = propose_covers(g, h)
        self.assertEqual(sorted(len(c['tasks']) for c in covers), [1, 2])
        for c in covers:
            p = Planner(c, h).solve(seconds=4)
            verify(c, h, p)
        self.assertEqual(covers[0]['cover_trace']['priority'], 4)

    def test_fanout_cannot_disappear_inside_fusion(self):
        g, h = fixture()
        h['services']['pair'] = {**h['services']['left'], 'op': 'pair', 'ticks': 4,
            'pattern': ['add', 'add'], 'pattern_numeric': ['test-int16'] * 2,
            'pattern_attributes': [{}, {}], 'pattern_inputs': [[0, 0]]}
        g['tasks'].append({'id': 'c', 'op': 'add', 'numeric': 'test-int16', 'inputs': ['a.out'], 'outputs': ['c.out']})
        g['values']['c.out'] = {'words': 1, 'producer': 'c'}
        self.assertTrue(all(len(c['tasks']) == 3 for c in propose_covers(g, h)))

    def test_compile_outputs_share_the_verified_plan(self):
        g, h = fixture()
        g['lowered'] = True
        result = compile_model(g, h, seconds=1, rounds=1)
        self.assertEqual(result['status'], 'planned')
        requests = result['outputs']['program_ir']['requests']
        events = {r['complete_event'] for r in requests}
        self.assertTrue(all(e.startswith('initial:') or e in events for r in requests for e in r['wait_for']))
        self.assertEqual({n['id'] for n in result['outputs']['wiring']['nets']}, set(result['plan']['nets']))
        self.assertFalse(result['outputs']['wiring']['physical_signoff'])


if __name__ == '__main__':
    unittest.main()
