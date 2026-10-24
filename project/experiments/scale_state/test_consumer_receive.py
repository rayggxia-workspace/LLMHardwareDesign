"""Standalone receiver tests use hand-built data, never producer imports."""
from fractions import Fraction
import json
from pathlib import Path
import tempfile
import unittest
import numpy as np
from consumer_receive import (artifact, arrays, compile_dyadic, delta_check, encode,
                              fields, k128_check, linear_check, metric, packet,
                              quant_check, real, rms, sha, verify_profile, write_npz)


class IndependentConsumerReceiver(unittest.TestCase):
    def test_offline_frexp_compiler_fraction(self):
        rng = np.random.default_rng(6001)
        w = rng.normal(size=(3, 256)).astype(np.float32)
        w[0, :128] = 0
        q, e = compile_dyadic(w, 128)
        self.assertEqual(int(e[0, 0]), -30)
        for n, col in np.ndindex(w.shape):
            unit = int(e[n, col//128]); value = Fraction(float(w[n, col]))*Fraction(2)**(-unit)
            self.assertEqual(int(q[n, col]), max(-127, min(127, round(value))))
        base = compile_dyadic(np.array([[127., 0.], [1., 0.]], dtype=np.float32), twice=True)
        self.assertEqual(base.tolist(), [1, -30])

    def test_encoding_and_same_range_fraction(self):
        x = np.tile(np.array([-1., -.5, 0., .5, 1., 2., -2., 0.], dtype=np.float32), 16)[None]
        source, q, e, witnesses = encode(x)
        self.assertEqual(q.shape, (1, 128)); self.assertEqual(witnesses, 2)
        for j in range(128): self.assertEqual(int(q[0, j]), round(Fraction(int(source[0, j]))*Fraction(2)**(-20-int(e[0, 0]))))
        a = np.array([[-128, 127, 128]], dtype=np.int64); u = np.zeros_like(a, dtype=np.int16)
        count, sat = quant_check(a, u, u-8, np.array([[-32768, 32512, 32512]], dtype=np.int16), 16)
        self.assertEqual((count, sat), (3, 1))

    def test_wide_linear_all_integer_oracle_and_tamper(self):
        a = np.ones((2, 256), dtype=np.int8)
        w = np.full((16, 256), 2, dtype=np.int8)
        ae = np.array([[-3, -2], [-2, -3]], dtype=np.int8)
        we = np.tile(np.array([[-4, -5]], dtype=np.int8), (16, 1))
        units = ae.T[:, :, None].astype(np.int16)+we.T[:, None, :].astype(np.int16)
        e0 = units.min(0); parts = np.full((2, 2, 16), 256, dtype=np.int32)
        acc = sum(parts[g].astype(np.int64)*(1 << (units[g]-e0)) for g in range(2))
        stored = dict(parts=parts, units=units, e0=e0, acc=acc)
        _, _, count = linear_check(a, ae, w, we, stored, True)
        self.assertEqual(count['I64_partial_values'], 64)
        stored['parts'][0, 0, 0] += 1
        with self.assertRaisesRegex(ValueError, 'I64 group'): linear_check(a, ae, w, we, stored)

    def test_delta_minimality_and_per_channel_base(self):
        acc = np.zeros((1, 32), dtype=np.int64); acc[0, 0] = 127
        units = np.full(acc.shape, -10, dtype=np.int16); base = np.full(32, -7, dtype=np.int8)
        delta = np.array([[-3, 0]], dtype=np.int8)
        self.assertGreater(delta_check(acc, units, base, delta), 0)
        delta[0, 0] = -2
        with self.assertRaisesRegex(ValueError, 'finest'): delta_check(acc, units, base, delta)

    def test_explicit_k128_conversion(self):
        code = np.full((1, 128), 64, dtype=np.int8)
        unit = np.full((1, 128), -5, dtype=np.int16); unit[:, 64:] = -4
        actual = np.full((1, 128), 64, dtype=np.int8); actual[:, :64] = 32
        actual_unit = np.full((1, 128), -4, dtype=np.int8); group_unit = np.array([[-4]], dtype=np.int8)
        self.assertEqual(k128_check(code, unit, actual, actual_unit, group_unit), 128)
        actual[0, 0] += 1
        with self.assertRaisesRegex(ValueError, 'Fraction K128'): k128_check(code, unit, actual, actual_unit, group_unit)

    def test_fp32_norm_recipe_and_packet(self):
        x = np.arange(128, dtype=np.float32)[None]/64
        gamma = np.zeros(128, dtype=np.float32)
        # Explicit independent FP32 RMS identity, including raw gamma+1.
        expected = x*np.reciprocal(np.sqrt(np.mean(x*x, axis=-1, keepdims=True, dtype=np.float32)+np.float32(1e-6)))
        self.assertTrue(np.array_equal(rms(x, gamma), expected))
        self.assertEqual(packet(64), 128); self.assertEqual(packet(65), 192)

    def test_full_static_profile_actual_rehashed_negative(self):
        H, K, N, R = 128, 128, 16, 1
        zero_hidden = np.zeros((R, H), dtype=np.float32)
        raw = {'weight.down': np.zeros((H, K), dtype=np.float32), 'weight.next_norm': np.zeros(H, dtype=np.float32)}
        for name in ['down', 'residual', 'sum', 'norm']: raw['prefill.'+name] = zero_hidden
        raw['prefill.projection'] = np.zeros((R, N), dtype=np.float32)
        common = {'prefill.down.acc': np.zeros((R, H), dtype=np.int64), 'prefill.down.e0': np.full((R, H), -40, dtype=np.int16),
                  'prefill.down.parts': np.zeros((1, R, H), dtype=np.int32), 'prefill.down.units': np.full((1, R, H), -40, dtype=np.int16)}
        for prefix in ['prefill.native_norm_projection.', 'prefill.pre_outlet.next.']:
            common[prefix+'acc'] = np.zeros((R, N), dtype=np.int64); common[prefix+'e0'] = np.full((R, N), -50, dtype=np.int16)
        nw = np.zeros((N, H), dtype=np.int8); ne = np.full((N, 1), -30, dtype=np.int8)
        base = np.full(H, -30, dtype=np.int8); next_base = np.full(N, -30, dtype=np.int8)
        z = {'outlet_codes': np.zeros((R, H), dtype=np.int8), 'outlet_units': np.full((R, H), -30, dtype=np.int16),
             'outlet_delta': np.empty((R, 0), dtype=np.int8), 'transport_codes': np.zeros((R, H), dtype=np.int8),
             'transport_units': np.full((R, H), -30, dtype=np.int16), 'K128_exponents': np.empty((R, 0), dtype=np.int8),
             'residual_S32Q20': np.zeros((R, H), dtype=np.int32), 'sum_acc64': np.zeros((R, H), dtype=np.int64),
             'sum_units': np.full((R, H), -30, dtype=np.int16), 'sum_F32_bridge': zero_hidden,
             'norm_F32_bridge': zero_hidden, 'norm_source_S32Q20': np.zeros((R, H), dtype=np.int32),
             'next.A8': np.zeros((R, H), dtype=np.int8), 'next.Ae': np.full((R, 1), -20, dtype=np.int8),
             'next.parts': np.zeros((1, R, N), dtype=np.int32), 'next.units': np.full((1, R, N), -50, dtype=np.int16),
             'next.acc': np.zeros((R, N), dtype=np.int64), 'next.e0': np.full((R, N), -50, dtype=np.int16),
             'next.final_ACT8': np.zeros((R, N), dtype=np.int8), 'next.final_units': np.full((R, N), -30, dtype=np.int16)}
        cost = {'rows': 1, 'complete_hidden_channels': H, 'next_projection_selected_outputs': N, 'source_down_full_K': K,
                'ACT_payload_bytes': H, 'static_base_exponent_bytes': H, 'incoming_tile16_delta_bytes': 0,
                'outgoing_scale_metadata_bytes': 0, 'complete_row_packet_bytes_static_base_resident': packet(H+32),
                'initial_base_scale_wire_bytes': packet(H), 'original_outlet_per16output_tile_packet_bytes_explicit_scale': 8*packet(64),
                'one_row_exact_residual_S64_plus_I16_units_bytes': H*10, 'one_row_F32_norm_buffer_bytes': H*4,
                'F32_norm_gamma_bytes': H*4, 'down_W8_total_bytes': H*K, 'down_W128_exponent_total_bytes': H,
                'one16output_down_W128_scale_bytes': 16, 'one16output_fixed_W_L1_U32_certificate_bytes_if_used': 64,
                'next_projection_W8_bytes': N*H, 'next_projection_W128_scale_bytes': N,
                'norm_V16KiB_capacity': {'exact_sum_and_units_fit': True, 'one_inplace_F32_row_fits': True, 'row_and_gamma_simultaneously_fit': True},
                'single128bit_1RW_bank_lower_bound_beats': {'ACT_write_read': 16, 'wide_sum_write_read': 128, 'unit_write_read': 32, 'norm_gamma_read': 32},
                'next_projection_input': 'fresh A8K128', 'scope': 'no finite scheduler', 'integer_work': {'saturation': 0}}
        record = {name: {'relative_rmse': 0., 'max_abs': 0.} for name in [
            'upstream_down_before_outlet_RQ_vs_native', 'down_after_outlet_RQ_vs_native', 'transport_requant_vs_outlet',
            'sum_vs_native', 'norm_vs_native', 'next_projection_vs_native', 'next_projection_vs_native_norm_same_W8A8',
            'next_projection_vs_upstream_no_outlet_RQ', 'native_norm_W8A8_vs_native_projection', 'next_final_ACT8_vs_native']}
        record.update(costs=cost, next_final_RQ={'saturation': 0}, integer_norm_implemented=False,
                      complete_next8192_projection=False, full_model_quality_accepted=False, hardware_performance_accepted=False)
        count = verify_profile(z, 'prefill', 'static_ACT8', common, raw, record, nw, ne, base, next_base)
        self.assertEqual(count['Fraction_residual_values'], 128)
        task = Path('D:/Projects/Codex/issue66-scale-state-20261024/consumer'); task.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='receive-test-', dir=task) as folder:
            root = Path(folder); z['outlet_codes'][0, 0] = 1
            path = root/'mutated.npz'; write_npz(path, z)
            manifest = {'artifacts': {path.name: {'bytes': path.stat().st_size, 'sha256': sha(path)}}}
            (root/'manifest.json').write_text(json.dumps(manifest)); artifact(root, manifest)
            with self.assertRaisesRegex(ValueError, 'Fraction outlet'):
                verify_profile(arrays(path), 'prefill', 'static_ACT8', common, raw, record, nw, ne, base, next_base)


if __name__ == '__main__': unittest.main()
