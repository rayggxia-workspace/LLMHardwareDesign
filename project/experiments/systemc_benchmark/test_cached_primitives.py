"""Runtime state is data, never a baked weight or a fake S16 input."""
import importlib.util
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
FROZEN = ROOT / 'work/YUZE-LU/234/raw/frozen220/project/experiments/block_synthesis'


@unittest.skipUnless(FROZEN.is_dir(), 'requires SHA-pinned old220 source fixture')
class CachedStateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(FROZEN))
        from full_integer import Q
        cls.Q = Q
        spec = importlib.util.spec_from_file_location('cached_primitives', Path(__file__).with_name('cached_primitives.py'))
        cls.module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.module
        spec.loader.exec_module(cls.module)
        spec = importlib.util.spec_from_file_location('old_wide_program', FROZEN / 'wide_program.py')
        cls.old = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = cls.old
        spec.loader.exec_module(cls.old)

    def build(self):
        Q = self.Q
        model = {'sha256': 'test-only', 'values': {
            'input_ids': {'shape': [1, 1]}, 'past': {'shape': [1, 2]},
            'new': {'shape': [1, 1]}, 'joined': {'shape': [1, 3]}},
            'outputs': ['joined'], 'tasks': [{'id': 'append', 'op': 'Concat',
                'inputs': ['past', 'new'], 'outputs': ['joined'], 'attributes': {'axis': -1}}]}
        initial = {'past': Q(np.zeros((1, 2), dtype=np.int32), -20),
                   'new': Q(np.array([[7]], dtype=np.int16), -20)}
        program = self.module.compile_program(model, initial, {}, {'joined': -20},
            runtime_formats={'past': {'shape': [1, 2], 'bits': 32, 'exponent': -20}})
        return program, initial

    def test_s32_state_not_truncated_or_frozen(self):
        p, initial = self.build()
        self.assertEqual(p['initial_formats']['past']['bits'], 32)
        self.assertNotIn('literal', p['initial_formats']['past'])
        for data in ([[100000, -100000]], [[-654321, 765432]]):
            output = self.module.execute(p, initial, [[1]], None,
                runtime_values={'past': self.Q(np.array(data, dtype=np.int32), -20)})['joined']
            np.testing.assert_array_equal(output.raw, [data[0] + [7]])
            self.assertEqual(output.exponent, -20)

    def test_state_contract_rejects_missing_wrong_shape_scale_range(self):
        p, initial = self.build()
        bad = ({}, {'past': self.Q(np.ones((2, 1), dtype=np.int32), -20)},
               {'past': self.Q(np.ones((1, 2), dtype=np.int32), -19)},
               {'past': self.Q(np.full((1, 2), 1 << 35, dtype=np.int64), -20)})
        for state in bad:
            with self.assertRaises(ValueError):
                self.module.execute(p, initial, [[1]], None, runtime_values=state)

    def test_token_shape_checked(self):
        p, initial = self.build()
        with self.assertRaises(ValueError):
            self.module.execute(p, initial, [[1, 2]], None,
                runtime_values={'past': initial['past']})

    def test_default_rms_program_keeps_the_frozen_recipe_instruction_for_instruction(self):
        raw = np.arange(-16, 16, dtype=np.int16).reshape(1, 32)
        initial = {'x': self.Q(raw, -10), 'gamma': self.Q(np.ones(32, dtype=np.int16), 0),
                   'eps': self.Q(np.array(1, dtype=np.int16), -20)}
        model = {'sha256': 'rms-default', 'values': {'input_ids': {'shape': [1, 1]},
            'x': {'shape': [1, 32]}, 'out': {'shape': [1, 32]}}, 'outputs': ['out'],
            'tasks': [{'id': 'rms', 'op': 'RMSNorm', 'inputs': ['x', 'gamma', 'eps'],
                       'outputs': ['out'], 'attributes': {}}]}
        calibration = {'values': {'x': {'symmetric_s16_exponent': -10}}}
        old = self.old.compile_program(model, initial, calibration, {'out': -20})
        current = self.module.compile_program(model, initial, calibration, {'out': -20})
        for field in ('instructions', 'outputs', 'predicates', 'value_bindings', 'initial_formats'):
            self.assertEqual(old[field], current[field], field)

    def test_heterogeneous_row_scale_exposes_single_refinement_error(self):
        import math
        class IndependentFactor:
            def factor(self, x, epsilon, l2=False):
                values = [int(v) for v in np.asarray(x).reshape(-1)]
                total = sum(v*v for v in values) << 16
                if not l2:
                    total //= len(values)
                return (1 << 38)//math.isqrt(total+(epsilon << 16))
        rng = np.random.default_rng(234)
        x = rng.normal(0, .2, (1, 2, 2048))
        x[0, 0, 0] = 2516.5
        raw = np.rint(x*2048).astype(np.int32)
        initial = {'x': self.Q(raw, -11), 'gamma': self.Q(np.full(2048, 32767, dtype=np.int16), -15),
                   'eps': self.Q(np.array(17180, dtype=np.int16), -34)}
        model = {'sha256': 'rms-heterogeneous', 'values': {'input_ids': {'shape': [1, 1]},
            'x': {'shape': list(raw.shape)}, 'out': {'shape': list(raw.shape)}}, 'outputs': ['out'],
            'tasks': [{'id': 'rms', 'op': 'RMSNorm', 'inputs': ['x', 'gamma', 'eps'],
                       'outputs': ['out'], 'attributes': {}}]}
        calibration = {'values': {'x': {'symmetric_s16_exponent': -3}}}
        runtime = {'x': {'shape': list(raw.shape), 'bits': 32, 'exponent': -11}}
        data = raw.astype(np.float64)/2048
        target = data/np.sqrt(np.mean(data*data, axis=-1, keepdims=True)+17180*2.**-34)*(32767/32768)
        errors, sizes = [], []
        for refinements in (1, 3):
            program = self.module.compile_program(model, initial, calibration, {'out': -20},
                runtime_formats=runtime, rms_refinements=refinements)
            out = self.module.execute(program, initial, [[0]], IndependentFactor(), runtime_values={'x': initial['x']})['out']
            result = out.raw.astype(np.float64)*2.**out.exponent
            errors.append(np.linalg.norm(result-target)/np.linalg.norm(target))
            sizes.append(len(program['instructions']))
        self.assertGreater(errors[0], .01)
        self.assertLess(errors[1], .001)
        self.assertGreater(sizes[1], sizes[0])

    def test_host_observer_sees_emitted_values_without_changing_results(self):
        p, initial = self.build()
        runtime = {'past': self.Q(np.array([[100000, -200000]], dtype=np.int32), -20)}
        plain = self.module.execute(p, initial, [[1]], None, runtime_values=runtime)
        seen = []
        traced = self.module.execute(p, initial, [[1]], None, runtime_values=runtime,
            observer=lambda node, q: seen.append((node['id'], q.exponent, q.raw.copy())))
        self.assertEqual([n['id'] for n in p['instructions']], [n for n, _, _ in seen])
        for name, value in plain.items():
            self.assertEqual(value.exponent, traced[name].exponent)
            np.testing.assert_array_equal(value.raw, traced[name].raw)

    def test_neg_and_retained_shared_output(self):
        p, initial = self.build()
        # A declared output must survive even when another instruction consumes it.
        joined = p['outputs']['joined']
        p['instructions'].extend([
            {'id': 'minus_one', 'op': 'Constant', 'inputs': [], 'shape': [],
             'exponent': 0, 'bits': 32, 'attributes': {'raw': -1}},
            {'id': 'negative', 'op': 'Product', 'inputs': [joined, 'minus_one'],
             'shape': [1, 3], 'exponent': -20, 'bits': 32,
             'attributes': {'shift': 0}}])
        p['outputs']['negative'] = 'negative'
        out = self.module.execute(p, initial, [[1]], None,
            runtime_values={'past': self.Q(np.array([[100000, -200000]], dtype=np.int32), -20)})
        np.testing.assert_array_equal(out['joined'].raw, [[100000, -200000, 7]])
        np.testing.assert_array_equal(out['negative'].raw, [[-100000, 200000, -7]])

    def test_legacy_program_and_replay_unchanged(self):
        from exact_reference_dot import ExactReferenceDot
        rng = np.random.default_rng(220)
        initial = {'x': self.Q(rng.integers(-1000, 1000, (2, 128), dtype=np.int16), -10),
                   'w': self.Q(rng.integers(-1000, 1000, (128, 3), dtype=np.int16), -12)}
        model = {'sha256': 'legacy-fixture', 'values': {'input_ids': {'shape': [1, 1]},
            'x': {'shape': [2, 128]}, 'w': {'shape': [128, 3]}, 'out': {'shape': [2, 3]}},
            'outputs': ['out'], 'tasks': [{'id': 'mm', 'op': 'MatMul',
                'inputs': ['x', 'w'], 'outputs': ['out'], 'attributes': {}}]}
        old = self.old.compile_program(model, initial, {}, {'out': -18})
        new = self.module.compile_program(model, initial, {}, {'out': -18})
        self.assertEqual(old['instructions'], new['instructions'])
        self.assertEqual(old['initial_formats'], new['initial_formats'])
        expected = self.old.execute(old, initial, [[1]], None)['out']
        actual = self.module.execute(new, initial, [[1]], None,
            dot_executor=ExactReferenceDot())['out']
        self.assertEqual(expected.exponent, actual.exponent)
        np.testing.assert_array_equal(expected.raw, actual.raw)

    def test_output_scale_change_is_an_emitted_rne_convert(self):
        # The fixture's output is produced by Concat. Add a final conversion
        # explicitly, including signed ties; no hidden rescale at handoff.
        model = {'sha256': 'explicit-output-fixture', 'values': {
            'input_ids': {'shape': [1, 1]}, 'x': {'shape': [1, 4]}, 'out': {'shape': [1, 4]}},
            'outputs': ['out'], 'tasks': [{'id': 'view', 'op': 'Identity',
                'inputs': ['x'], 'outputs': ['out'], 'attributes': {}}]}
        initial = {'x': self.Q(np.array([[3, 5, -3, -5]], dtype=np.int16), -20)}
        p = self.module.compile_program(model, initial, {}, {'out': -20}, output_formats={
            'out': {'shape': [1, 4], 'bits': 32, 'exponent': -19}})
        self.assertEqual(p['instructions'][-1]['op'], 'Convert')
        self.assertEqual(p['instructions'][-1]['kernel'], 'view')
        q = self.module.execute(p, initial, [[1]], None)['out']
        np.testing.assert_array_equal(q.raw, [[2, 2, -2, -2]])
        self.assertEqual(q.exponent, -19)


if __name__ == '__main__':
    unittest.main()
