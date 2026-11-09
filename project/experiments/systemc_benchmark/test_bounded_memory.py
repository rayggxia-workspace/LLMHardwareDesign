import copy
import unittest

import numpy as np

from bounded_memory import Arena, audit_intervals, dense_file_layout, plan_serial


class FiniteBacking(unittest.TestCase):
    def program(self):
        return {'initial_formats': {'x': {'shape': [4], 'bits': 32, 'runtime': True}},
            'input_ids_shape': [1, 1], 'outputs': {'out': 'v2'},
            'instructions': [
                {'id': 'v0', 'op': 'View', 'inputs': ['x'], 'shape': [2], 'attributes': {'view_op': 'Slice'}},
                {'id': 'v1', 'op': 'Convert', 'inputs': ['x'], 'shape': [4], 'attributes': {}},
                {'id': 'v2', 'op': 'Convert', 'inputs': ['v0'], 'shape': [2], 'attributes': {}}]}

    def test_view_retains_whole_backing_until_its_last_consumer(self):
        plan = plan_serial(self.program(), 9, 1)
        self.assertEqual(plan['allocations']['x']['last'], 2)
        self.assertEqual(plan['bindings']['v0']['owner'], 'x')
        self.assertTrue(audit_intervals(plan)['passed'])
        with self.assertRaises(MemoryError):
            plan_serial(self.program(), 8, 1)
        # Independently turn a safe reuse into an overlapping live allocation.
        bad = copy.deepcopy(plan)
        bad['allocations']['v1']['address_words'] = bad['allocations']['x']['address_words']
        with self.assertRaisesRegex(ValueError, 'simultaneous address overlap'):
            audit_intervals(bad)

    def test_physical_reuse_rejects_old_generation_and_bounds(self):
        arena = Arena(4)
        a = arena.allocate('old', 4)
        arena.release('old')
        b = arena.allocate('new', 4)
        self.assertEqual(a['address_words'], b['address_words'])
        with self.assertRaisesRegex(ValueError, 'stale'):
            arena.locate('new', a['generation'], 0)
        with self.assertRaisesRegex(ValueError, 'stale'):
            arena.locate('old', a['generation'], 0)
        with self.assertRaisesRegex(ValueError, 'out-of-bounds'):
            arena.locate('new', b['generation'], 4)

    def test_dense_transposed_weight_shares_physical_records_and_values(self):
        a = {'shape': [2, 3], 'bits': 16, 'source_file': 'frozen.npy',
             'source_offset_bytes': 128, 'source_byte_strides': [6, 2]}
        b = dict(a, shape=[3, 2], source_byte_strides=[2, 6])
        p = {'initial_formats': {'w': a, 'wt': b}, 'input_ids_shape': [1, 1],
             'outputs': {'a': 'w', 'b': 'wt'}, 'instructions': []}
        plan = plan_serial(p, 7, 1)
        self.assertEqual(plan['bindings']['w']['owner'], plan['bindings']['wt']['owner'])
        self.assertEqual(plan['physical_initial_file_groups'], 1)
        raw = np.arange(6).reshape(2, 3)
        for name, expected in (('w', raw), ('wt', raw.T)):
            strides = plan['bindings'][name]['record_strides']
            for coord in np.ndindex(expected.shape):
                offset = sum(i*s for i, s in zip(coord, strides))
                self.assertEqual(raw.reshape(-1)[offset], expected[coord])
        with self.assertRaisesRegex(ValueError, 'complete dense permutation'):
            dense_file_layout(dict(a, source_byte_strides=[4, 2]))

    def test_constants_are_preloaded_and_cannot_be_free_runtime_writes(self):
        p = self.program()
        p['instructions'].append({'id': 'constant', 'op': 'Constant', 'inputs': [],
                                   'shape': [1], 'attributes': {'raw': 7}})
        p['outputs']['constant'] = 'constant'
        plan = plan_serial(p, 10, 1)
        self.assertEqual(plan['allocations']['constant']['born'], -1)
        self.assertTrue(plan['allocations']['constant']['pinned'])
        self.assertTrue(audit_intervals(plan)['passed'])
