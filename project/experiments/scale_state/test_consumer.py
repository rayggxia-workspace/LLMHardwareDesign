"""Integer and full-hidden contract tests; no remote/model task is launched."""
from fractions import Fraction
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from consumer import (PROFILES, bridge, checked, compile_weights, convert_k128,
                      cost, delta_tiles, encode_rows, error, fraction_rne, linear,
                      npz, output_base, packets, physical, quant_output,
                      residual_add, rms_float, rne, sha, verify_capture)


class ConsumerContract(unittest.TestCase):
    def test_signed_rne_against_fraction_and_domains(self):
        for value in [-2147483648, -129, -7, -5, -3, -1, 0, 1, 3, 5, 7, 129, 2147483647]:
            for shift in [-8, -1, 0, 1, 2, 7, 31, 63]:
                wanted = round(Fraction(value)*Fraction(2)**(-shift))
                self.assertEqual(rne(value, shift), wanted)
                self.assertEqual(fraction_rne(Fraction(value)*Fraction(2)**(-shift)), wanted)
        with self.assertRaises(OverflowError): rne(1, 64)
        with self.assertRaises(OverflowError): checked(1 << 63)

    def test_source_bridges_zero_tail_and_float_rejection(self):
        source, a, e, count = encode_rows(np.zeros((2, 128), dtype=np.float32))
        self.assertFalse(source.any()); self.assertFalse(a.any())
        self.assertTrue(np.all(e == -20)); self.assertEqual(count, 4)
        for bad in [float('nan'), float('inf'), 2048.]:
            with self.assertRaises(OverflowError): bridge(np.array([[bad]]))
        with self.assertRaises(ValueError): encode_rows(np.zeros((1, 127)))
        with self.assertRaises(ValueError): compile_weights(np.zeros((16, 127)))
        with self.assertRaises(ValueError): compile_weights(np.full((16, 128), np.nan))

    def test_complete_mixed_unit_linear_full_i64_and_python_oracles(self):
        rng = np.random.default_rng(71)
        a = rng.integers(-127, 128, (3, 256), dtype=np.int16).astype(np.int8)
        w = rng.integers(-127, 128, (16, 256), dtype=np.int16).astype(np.int8)
        ae = np.array([[-10, -8], [-9, -12], [-12, -9]], dtype=np.int8)
        we = rng.integers(-12, -7, (16, 2), dtype=np.int8)
        result, stats = linear(a, ae, w, we)
        for r, c in np.ndindex(result['acc'].shape):
            unit = int(result['e0'][r, c]); expected = 0
            for g in range(2):
                part = sum(int(x)*int(y) for x, y in zip(a[r, g*128:(g+1)*128], w[c, g*128:(g+1)*128]))
                expected += part << (int(ae[r, g])+int(we[c, g])-unit)
            self.assertEqual(int(result['acc'][r, c]), expected)
        self.assertEqual(stats['INT64_partial_values_checked'], 96)
        ae[0, 0] = -80
        with self.assertRaises(OverflowError): linear(a, ae, w, we)

    def test_exact_same_range_act16_and_saturation(self):
        acc = np.array([[-129, -128, 127, 128]], dtype=np.int64)
        units = np.zeros_like(acc, dtype=np.int16)
        c8, s8 = quant_output(acc, units, units, 8)
        c16, s16 = quant_output(acc, units, units-8, 16)
        self.assertTrue(np.array_equal(physical(c8, units), physical(c16, units-8)))
        self.assertEqual(c16.tolist(), [[-32768, -32768, 32512, 32512]])
        self.assertEqual(s8['saturation'], s16['saturation'])

    def test_delta_is_per_tile_and_base_remains_per_channel(self):
        acc = np.zeros((1, 128), dtype=np.int64)
        acc[0, 0] = 3; acc[0, 16] = 127
        units = np.full(acc.shape, -10, dtype=np.int16)
        base = np.array([-7, -8]*64, dtype=np.int8)
        delta, stats = delta_tiles(acc, units, base)
        effective = base[None].astype(np.int16)+np.repeat(delta.astype(np.int16), 16, axis=1)
        self.assertNotEqual(int(effective[0, 0]), int(effective[0, 1]))
        self.assertNotEqual(int(delta[0, 0]), int(delta[0, 1]))
        self.assertTrue(np.all(delta[0, 2:] == 0))
        c, s = quant_output(acc, units, effective, 8)
        self.assertEqual(s['saturation'], 0)
        self.assertGreater(stats['delta_RNE_compare_terms'], 0)
        with self.assertRaises(ValueError): delta_tiles(acc[:, :17], units[:, :17], base[:17])
        with self.assertRaises(OverflowError): delta_tiles(np.full((1, 16), 127, dtype=np.int64), np.full((1, 16), 20), np.full(16, -20))

    def test_k128_conversion_preserves_units_then_rne(self):
        codes = np.tile(np.array([-128, -7, -1, 0, 1, 7, 64, 127], dtype=np.int8), 16)[None]
        units = np.tile(np.array([-12, -11, -10, -9], dtype=np.int16), 32)[None]
        new, effective, exponent, stats = convert_k128(codes, units)
        self.assertEqual(exponent.shape, (1, 1))
        for j in range(128):
            self.assertEqual(int(new[0, j]), round(Fraction(int(codes[0, j]))*Fraction(2)**(int(units[0, j])-int(effective[0, j]))))
        self.assertLessEqual(int(np.max(abs(new.astype(np.int16)))), 127)
        self.assertEqual(stats['Fraction_K128_conversion_values'], 128)
        zeros = np.zeros((1, 128), dtype=np.int8)
        converted, _, _, _ = convert_k128(zeros, np.full(zeros.shape, -20))
        self.assertFalse(converted.any())
        with self.assertRaises(ValueError): convert_k128(codes[:, :16], units[:, :16])

    def test_integer_residual_fraction_and_checked_intermediate(self):
        codes = np.array([[127, -128, 3, -3]], dtype=np.int16)
        units = np.array([[-7, -10, -30, -3]], dtype=np.int16)
        residual = np.array([[.5, -.125, 1., -2.]], dtype=np.float32)
        r32, summed, common, stats = residual_add(codes, units, residual)
        for index in np.ndindex(codes.shape):
            expected = Fraction(int(codes[index]))*Fraction(2)**int(units[index])+Fraction(int(r32[index]), 1 << 20)
            self.assertEqual(Fraction(int(summed[index]))*Fraction(2)**int(common[index]), expected)
        self.assertEqual(stats['Fraction_residual_add_values'], 4)
        with self.assertRaises(OverflowError): residual_add(np.array([[127]]), np.array([[50]]), np.array([[1.]], dtype=np.float32))

    def test_full_hidden_rmsnorm_effective_one_plus_weight(self):
        source = np.ones((1, 128), dtype=np.float32); source[0, -1] = 10
        raw_gamma = np.zeros(128, dtype=np.float32)
        got = rms_float(source, raw_gamma)
        wanted = source/np.sqrt(np.mean(source*source, axis=-1, keepdims=True)+np.float32(1e-6))
        self.assertTrue(np.allclose(got, wanted, atol=1e-7))
        clipped = rms_float(source[:, :16], raw_gamma[:16])
        self.assertGreater(abs(float(clipped[0, 0]-got[0, 0])), .2)
        self.assertTrue(np.allclose(rms_float(source, np.ones(128, dtype=np.float32)), got*2))

    def test_full_hidden_small_chain_all_four_profiles(self):
        rng = np.random.default_rng(20261024)
        W = rng.normal(0, .03, (128, 256)).astype(np.float32)
        NW = rng.normal(0, .03, (16, 128)).astype(np.float32)
        A = rng.normal(0, .4, (4, 256)).astype(np.float32)
        residual = rng.normal(0, .5, (4, 128)).astype(np.float32)
        raw_gamma = rng.normal(0, .05, 128).astype(np.float32)
        reference_down = A@W.T
        reference_norm = rms_float(reference_down+residual, raw_gamma)
        qw, ew, _ = compile_weights(W); nw, ne, _ = compile_weights(NW)
        _, aa, ae, _ = encode_rows(A); down, _ = linear(aa, ae, qw, ew)
        base = output_base(reference_down); delta, _ = delta_tiles(down['acc'], down['e0'], base)
        for profile in PROFILES:
            bits = 16 if profile == 'same_range_ACT16' else 8
            units = np.broadcast_to(base.astype(np.int16)[None], down['acc'].shape).copy()
            if bits == 16: units -= 8
            if 'delta' in profile: units += np.repeat(delta.astype(np.int16), 16, axis=1)
            codes, _ = quant_output(down['acc'], down['e0'], units, bits)
            if profile == 'delta_to_K128_ACT8': codes, units, _, _ = convert_k128(codes, units)
            _, summed, su, _ = residual_add(codes, units, residual)
            norm = rms_float(physical(summed, su).astype(np.float32), raw_gamma)
            _, a8, e8, _ = encode_rows(norm)
            projection, _ = linear(a8, e8, nw, ne)
            value = physical(projection['acc'], projection['e0'])
            self.assertEqual(value.shape, (4, 16))
            self.assertLess(error(value, reference_norm@NW.T)['relative_rmse'], .1)

    def test_capacity_packet_costs_are_explicit_lower_bounds(self):
        codes = np.zeros((1, 2560), dtype=np.int8)
        c = cost(2560, 9216, 16, 1, 'tile16_delta_ACT8', codes, np.zeros_like(codes), np.zeros((1, 160)), {})
        self.assertEqual(c['incoming_tile16_delta_bytes'], 160)
        self.assertFalse(c['norm_V16KiB_capacity']['exact_sum_and_units_fit'])
        self.assertTrue(c['norm_V16KiB_capacity']['one_inplace_F32_row_fits'])
        self.assertFalse(c['norm_V16KiB_capacity']['row_and_gamma_simultaneously_fit'])
        self.assertEqual(packets(64), 128)
        self.assertEqual(packets(65), 192)
        self.assertGreater(c['down_W8_total_bytes'], 8*32768)

    def test_capture_checksum_and_no_reserved_input(self):
        task = Path('D:/Projects/Codex/issue66-scale-state-20261024/consumer')
        task.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='consumer-test-', dir=task) as folder:
            root = Path(folder); raw = root/'consumer-raw.npz'; npz(raw, {'fixture': np.zeros(2)})
            m = {'status': 'PASS', 'model': {'id': 'Qwen/Qwen3.5-4B'}, 'artifacts': {'consumer-raw.npz': {'bytes': raw.stat().st_size, 'sha256': sha(raw)}}}
            (root/'manifest.json').write_text(json.dumps(m)); verify_capture(root)
            data = bytearray(raw.read_bytes()); data[-1] ^= 1; raw.write_bytes(data)
            with self.assertRaisesRegex(ValueError, 'SHA'): verify_capture(root)
            m['sealed_reserved'] = True; (root/'manifest.json').write_text(json.dumps(m))
            with self.assertRaisesRegex(ValueError, 'nonreserved'): verify_capture(root)


if __name__ == '__main__':
    unittest.main()
