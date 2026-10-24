"""Boundary/independent-oracle tests; no model download or remote execution."""
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np

from attention import (BOUNDS, GRIDS, I32_MAX, I32_MIN, bridge, compile_lut,
                       compile_scale, divide_rne_u64, evaluate, exponent, fixed,
                       fraction_rne, limbs16, npz, qk32, query, rne, score_q12,
                       sha, softmax_integer)


class IntegerAttention(unittest.TestCase):
    def test_shift_rne_fraction_ties_and_negative_domain(self):
        for value in [-2147483648, -129, -7, -5, -3, -1, 0, 1, 3, 5, 7, 129, 2147483647]:
            for shift in [-2, 0, 1, 2, 7, 31, 63]:
                self.assertEqual(rne(value, shift), round(Fraction(value) * Fraction(2)**(-shift)))
        self.assertEqual(rne(-3, 1), -2)
        self.assertEqual(rne(-5, 1), -2)
        with self.assertRaises(ValueError):
            rne(1, 64)

    def test_bridge_query_scale_and_kv_clipping(self):
        self.assertEqual(exponent(np.zeros(3, dtype=np.int32)), -20)
        self.assertEqual(exponent(np.array([-2147483648], dtype=np.int64)), 5)
        q, e = query(np.array([[[0., 0., 0.], [1., -2., 3.]]], dtype=np.float32))
        self.assertEqual(int(e[0, 0]), -20)
        self.assertFalse(q[0, 0].any())
        k, clips = fixed(np.array([-100., 1., 100.]), 8, -4)
        self.assertEqual(clips, 2)
        self.assertEqual(k.tolist(), [-127, 16, 127])
        for bad in [float('nan'), float('inf'), 2048.]:
            with self.assertRaises(OverflowError):
                bridge(np.array([bad]))

    def test_qk_all_digits_tail_dim_and_independent_i64(self):
        rng = np.random.default_rng(20261024)
        q = rng.integers(-127, 128, (3, 4, 71), dtype=np.int16).astype(np.int8)
        for bits in [8, 16]:
            limit = (1 << (bits-1)) - 1
            k = rng.integers(-limit, limit+1, (23, 71), dtype=np.int32)
            if bits == 16:
                k.flat[:5] = [-32767, -16384, -65, 64, 32767]
                d = limbs16(k)
                self.assertTrue(np.array_equal(sum(x.astype(np.int64) * 128**j for j, x in enumerate(d)), k))
            got, stat = qk32(q, k, bits)
            self.assertTrue(np.array_equal(got, q.astype(np.int64) @ k.astype(np.int64).T))
            self.assertEqual(stat['S8_dot_passes'], 3 if bits == 16 else 1)
        with self.assertRaises(OverflowError):
            qk32(np.zeros((1, 1, 512), dtype=np.int8), np.zeros((1, 512), dtype=np.int16), 16)
        with self.assertRaises(ValueError):
            qk32(np.array([[[-128]]], dtype=np.int8), np.ones((1, 1), dtype=np.int8), 8)

    def test_score_scaling_rounding_and_checked_widths(self):
        scale, meta = compile_scale(1 / np.sqrt(128))
        dot = np.array([[[7, -7, I32_MAX]]], dtype=np.int32)
        e = np.array([[-12]], dtype=np.int8)
        got, _ = score_q12(dot, e, -12, scale)
        wanted = [round(Fraction(int(v) * scale) * Fraction(2)**(-42)) for v in dot.flat]
        self.assertEqual(got.ravel().tolist(), wanted)
        self.assertLess(meta['absolute_error'], 2.**-30)
        for bad in [-1, 0, float('nan'), 4.]:
            with self.assertRaises((ValueError, OverflowError)):
                compile_scale(bad)
        with self.assertRaises(OverflowError):
            score_q12(np.array([[[I32_MAX]]]), np.array([[0]]), 0, 1 << 30)
        with self.assertRaises(ValueError):
            score_q12(np.array([[[1]]]), np.array([[100]]), 0, 1 << 30)

    def test_lut_extent_monotonic_endpoint_and_capacity(self):
        for grid, size in [(128, 8196), (256, 16388)]:
            table = compile_lut(grid)
            self.assertEqual(table.dtype, np.dtype('uint32'))
            self.assertEqual(table.nbytes, size)
            self.assertEqual(int(table[0]), 1 << 30)
            self.assertEqual(int(table[-1]), 121)
            self.assertTrue(np.all(table[1:] <= table[:-1]))
            self.assertGreater(table.nbytes, 8192)
        with self.assertRaises(ValueError):
            compile_lut(64)

    def test_u64_division_ties_and_max_boundary(self):
        numerator = np.array([1, 3, 5, 7, 8, (1 << 64)-1], dtype=np.uint64)
        denominator = np.array([2, 2, 2, 2, 3, (1 << 64)-1], dtype=np.uint64)
        got = divide_rne_u64(numerator, denominator)
        self.assertEqual(got.tolist(), [round(Fraction(int(n), int(d))) for n, d in zip(numerator, denominator)])
        # Test an odd near-U64 denominator: comparing 2*remainder would overflow.
        near = divide_rne_u64(np.array([(1 << 64)-2], dtype=np.uint64), np.array([(1 << 64)-1], dtype=np.uint64))
        self.assertEqual(near.tolist(), [1])
        with self.assertRaises(ZeroDivisionError):
            divide_rne_u64(np.array([1], dtype=np.uint64), np.array([0], dtype=np.uint64))

    def test_softmax_singleton_mask_threshold_and_fraction(self):
        for grid in GRIDS:
            lut = compile_lut(grid)
            # Includes exact max, threshold, one unit below threshold, and masked larger score.
            scores = np.array([[[0, -16*4096, -16*4096-1, I32_MAX]]], dtype=np.int32)
            mask = np.array([[True, True, True, False]])
            p, exp, den, budget, st = softmax_integer(scores, mask, grid, lut)
            self.assertEqual(exp[0, 0].tolist(), [1 << 30, 121, 0, 0])
            self.assertEqual(p[0, 0, 3], 0)
            self.assertEqual(st['truncated_active_exp_count'], 1)
            self.assertEqual(p.sum(), 32767)
            self.assertGreaterEqual(st['Fraction_probability_RNE_witnesses'], 3)
            one, _, _, _, _ = softmax_integer(np.array([[[I32_MIN]]], dtype=np.int32), np.array([[True]]), grid, lut)
            self.assertEqual(one.tolist(), [[[32767]]])
            with self.assertRaisesRegex(ValueError, 'fully masked'):
                softmax_integer(scores, np.zeros_like(mask), grid, lut)

    def test_softmax_lut_index_ties_and_long_uniform_psum(self):
        lut = compile_lut(128)
        scores = np.array([[[0, -16, -48, -80, -112]]], dtype=np.int32)
        _, ex, _, _, _ = softmax_integer(scores, np.ones((1, 5), dtype=bool), 128, lut)
        self.assertEqual(ex.ravel().tolist(), lut[[0, 0, 2, 2, 4]].tolist())
        for keys in [3, 128, 256, 1024, 4128]:
            score = np.zeros((2, 2, keys), dtype=np.int32)
            mask = np.ones((2, keys), dtype=bool)
            p, _, _, budget, _ = softmax_integer(score, mask, 128, lut)
            self.assertTrue(np.all(p.sum(-1) <= budget[None]))
            self.assertTrue(np.all(p > 0))
            self.assertEqual(int(p[0, 0, 0]), round(Fraction(32768, keys)))

    def test_complete_group_local_window_and_pv32(self):
        rng = np.random.default_rng(1003)
        q = rng.normal(size=(4, 5, 128)).astype(np.float32)
        k = rng.normal(size=(17, 128)).astype(np.float32)
        v = rng.normal(size=(17, 128)).astype(np.float32)
        positions = np.array([3, 5, 8, 12, 16])
        mask = (np.arange(17)[None] <= positions[:, None]) & (np.arange(17)[None] > positions[:, None]-4)
        logits = (q @ k.T) / np.sqrt(128)
        logits = np.where(mask[None], logits, -np.inf)
        prob = np.exp(logits-logits.max(-1, keepdims=True)); prob /= prob.sum(-1, keepdims=True)
        ref = prob @ v
        for bits in [8, 16]:
            report, arrays = evaluate(q, k, v, ref, k*2, v*2, positions, 4, 1/np.sqrt(128), bits, 256, compile_lut(256))
            self.assertFalse(arrays['P15'][:, ~mask].any())
            self.assertTrue(np.array_equal(arrays['PV32'], arrays['P15'].astype(np.int64) @ arrays['V'].astype(np.int64)))
            self.assertLess(report['integer_output_vs_FP64_same_encoded_KV_P15']['relative_rmse'], .02)
            self.assertFalse(report['operations']['softmax']['runtime_float_fallback'])
            self.assertEqual(report['operations']['PV']['S8_matmul_passes'], 9 if bits == 16 else 3)
            self.assertFalse(report['hardware_supported'])

    def test_zero_calibration_and_causal_query(self):
        zero = np.zeros((1, 1, 128), dtype=np.float32)
        kv = np.zeros((1, 128), dtype=np.float32)
        report, arrays = evaluate(zero, kv, kv, zero, kv, kv, np.array([0]), None,
                                  1/np.sqrt(128), 16, 128, compile_lut(128))
        self.assertEqual(report['K_exponent'], -20)
        self.assertEqual(report['V_exponent'], -20)
        self.assertEqual(arrays['P15'].item(), 32767)
        self.assertFalse(arrays['PV32'].any())

    def test_cli_manifest_input_hash_and_refuse_overwrite(self):
        task = Path('D:/Projects/Codex/issue64-block-v2-20261024/agent-attn')
        task.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='attention-test-', dir=task) as td:
            root = Path(td)
            rng = np.random.default_rng(77)
            models = [('gemma-capture01', 'google/gemma-3-4b-it'), ('qwen25-gqa01', 'Qwen/Qwen2.5-3B'), ('qwen35-gqa01', 'Qwen/Qwen3.5-4B')]
            for folder, name in models:
                capture = root/folder; capture.mkdir()
                arrays = {}
                for case in ['calibration', 'eval']:
                    q = rng.normal(0, .2, (2, 8, 16)).astype(np.float32)
                    k = rng.normal(0, .2, (8, 16)).astype(np.float32)
                    v = rng.normal(0, .2, (8, 16)).astype(np.float32)
                    mask = np.arange(8)[None] <= np.arange(8)[:, None]
                    score = np.where(mask[None], q@k.T*.25, -np.inf)
                    p = np.exp(score-score.max(-1, keepdims=True)); p /= p.sum(-1, keepdims=True)
                    for field, value in [('q', q), ('k', k), ('v', v), ('reference', p@v)]:
                        arrays[case+'.layer0.full.'+field] = value
                raw = capture/'selected-raw.npz'; npz(raw, arrays)
                manifest = {'status': 'PASS', 'model': {'id': name}, 'selected_layers': [0],
                            'cases': [{'name': 'calibration'}, {'name': 'eval', 'prefix': 4, 'full_events': [{'layer': 0, 'window': None, 'scaling': .25}]}],
                            'artifacts': {'selected-raw.npz': {'bytes': raw.stat().st_size, 'sha256': sha(raw)}}}
                (capture/'manifest.json').write_text(json.dumps(manifest))
            script = Path(__file__).with_name('attention.py')
            cmd = [sys.executable, '-B', str(script), '--root', str(root), '--out', str(root/'result')]
            done = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(done.returncode, 0, done.stderr)
            manifest = json.loads((root/'result/manifest.json').read_text())
            self.assertEqual(manifest['conditions'], 12)
            self.assertEqual(manifest['status'], 'PASS')
            self.assertEqual(len(manifest['input_captures']), 3)
            self.assertFalse(manifest['hardware_implemented'])
            self.assertEqual(manifest['source']['files']['server_models/bounds.py'], sha(BOUNDS))
            self.assertNotEqual(subprocess.run(cmd, capture_output=True).returncode, 0)
            # A valid-looking manifest cannot authorize rehashed or modified source tensors.
            raw = root/'qwen25-gqa01/selected-raw.npz'
            data = bytearray(raw.read_bytes()); data[-1] ^= 1; raw.write_bytes(data)
            cmd[-1] = str(root/'corrupt-result')
            rejected = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn('artifact mismatch', rejected.stderr)


if __name__ == '__main__':
    unittest.main()
