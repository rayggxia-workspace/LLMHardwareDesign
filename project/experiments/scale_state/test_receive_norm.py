import copy
from fractions import Fraction
import math
import unittest
import numpy as np
import receive_norm as r


class IndependentNormReceiver(unittest.TestCase):
    @staticmethod
    def revised_cost_fixture(H=2560, R=8, active=8):
        # Literals at the actual2560-hidden contract make a changed formula
        # unable to move the test expectation with the implementation.
        if H == 2560:
            aligned, fits, source2, source1, spill = 20480, False, 51200, 25600, 40960
            payload, exponents, packet_per_row = R*2560, R*20, 2752
            beats = dict(sum_and_units_two_reads=3200,
                         X16_write_then_norm_read_if_square_fused_at_encoding=640,
                         X16_write_square_read_norm_read_if_not_fused=960,
                         gamma_read=640, norm32_write_read=1280,
                         fresh_A8_write_read=320, fresh_Ae_write_read=4)
        elif H == 128:
            aligned, fits, source2, source1, spill = 1024, True, 2560, 1280, 2048
            payload, exponents, packet_per_row = R*128, R, 256
            beats = dict(sum_and_units_two_reads=160,
                         X16_write_then_norm_read_if_square_fused_at_encoding=32,
                         X16_write_square_read_norm_read_if_not_fused=48,
                         gamma_read=32, norm32_write_read=64,
                         fresh_A8_write_read=16, fresh_Ae_write_read=2)
        else:
            raise AssertionError('explicit fixture cases only')
        counts = dict(X16_Fraction_codes=R*H, norm_pre_gamma_Fraction_codes=R*H,
                      norm_gamma_Fraction_codes=R*H, fresh_A8_Fraction_codes=R*H,
                      isqrt_math_oracles=active, divider_Fraction_oracles=active,
                      isqrt_restoring_rounds=active*32, divide_restoring_rounds=active*64,
                      zero_rows=R-active)
        cost = dict(gamma_S32Q20_bytes=H*4, norm_S32Q20_row_bytes=H*4, X16_row_bytes=H*2,
                    mixed_sum_I64_plus_I16_row_bytes=H*10, inverse_U32Q30_bytes_per_row=4,
                    X16_square_products=active*H, U64_square_sum_add_terms=active*H,
                    S8_only_products_per_S16square_upper=9, S16xU32_products=active*H,
                    S32xS32_gamma_products=active*H, S8_only_products_per_S16xU32_upper=15,
                    S8_only_products_per_S32xS32_upper=25,
                    aligned_I64_row_bytes=aligned, aligned_I64_row_fits_V16KiB=fits,
                    finite_buffer_alternatives={
                        'two_source_passes': dict(sum_and_units_read_bytes_per_row=source2, aligned_spill_RW_bytes=0),
                        'aligned_spill': dict(sum_and_units_read_bytes_per_row=source1, aligned_spill_RW_bytes=spill)},
                    selected_candidate_buffer_route='two_source_passes; Python aligned list is software reference storage, not free V SRAM',
                    fresh_A8_payload_bytes=payload, fresh_A8_K128_exponent_bytes=exponents,
                    norm_to_M_row_packet_bytes=R*packet_per_row,
                    **{'1RW128bit_row_read_write_lower_bound_beats': beats},
                    buffer_scope='alternative accounts, not added together; no finite schedule')
        return dict(counts=counts, candidate_cost=cost)

    def test_revised_cost_packet_fifo_and_alternatives(self):
        row = self.revised_cost_fixture()
        r.verify_cost(row, 8, 2560, 8)
        small = self.revised_cost_fixture(H=128, R=3, active=2)
        r.verify_cost(small, 3, 128, 2)
        self.assertEqual(row['candidate_cost']['norm_to_M_row_packet_bytes'], 22016)
        self.assertEqual(small['candidate_cost']['norm_to_M_row_packet_bytes'], 768)

    def test_every_revised_numeric_ledger_field_rejects_corruption(self):
        original = self.revised_cost_fixture()
        paths = [('aligned_I64_row_bytes',), ('aligned_I64_row_fits_V16KiB',),
                 ('fresh_A8_payload_bytes',), ('fresh_A8_K128_exponent_bytes',),
                 ('norm_to_M_row_packet_bytes',)]
        paths += [('finite_buffer_alternatives', route, field)
                  for route in ('two_source_passes', 'aligned_spill')
                  for field in ('sum_and_units_read_bytes_per_row', 'aligned_spill_RW_bytes')]
        paths += [('1RW128bit_row_read_write_lower_bound_beats', field)
                  for field in original['candidate_cost']['1RW128bit_row_read_write_lower_bound_beats']]
        for path in paths:
            with self.subTest(path=path):
                altered = copy.deepcopy(original)
                node = altered['candidate_cost']
                for name in path[:-1]:
                    node = node[name]
                key = path[-1]
                node[key] = not node[key] if isinstance(node[key], bool) else node[key]+1
                with self.assertRaises(AssertionError):
                    r.verify_cost(altered, 8, 2560, 8)

    def test_old_or_partial_ledger_cannot_downgrade_new_account(self):
        original = self.revised_cost_fixture()
        for field in ('aligned_I64_row_bytes', 'finite_buffer_alternatives',
                      'selected_candidate_buffer_route', 'fresh_A8_K128_exponent_bytes'):
            with self.subTest(missing=field):
                altered = copy.deepcopy(original)
                del altered['candidate_cost'][field]
                with self.assertRaises(AssertionError):
                    r.verify_cost(altered, 8, 2560, 8)
        altered = copy.deepcopy(original)
        altered['candidate_cost']['buffer_scope'] = 'source and spill combined; no finite schedule'
        with self.assertRaises(AssertionError):
            r.verify_cost(altered, 8, 2560, 8)

    def test_decimal_constants_and_gamma_half_even(self):
        raw = np.array([0, 2**-21, 3*2**-21, -2**-21], np.float32)
        gamma, eps, sqrtH = r.constants(raw, 256)
        np.testing.assert_array_equal(gamma, [1048576, 1048576, 1048578, 1048576])
        self.assertEqual(eps, 1099512)
        self.assertEqual(sqrtH, 16*1048576)

    def test_exact_analytic_norm_epsilon_zero(self):
        H = 256
        sums = np.full((1, H), 1048576, np.int64)
        units = np.full(sums.shape, -20, np.int16)
        gamma = np.full(H, 1048576, np.int32)
        result = r.rms_oracle(sums, units, gamma, 0, 16*1048576)
        self.assertEqual(int(result['row_exponent'][0]), -14)
        self.assertEqual(int(result['sqrt_U32'][0]), 2**26)
        self.assertEqual(int(result['inv_Q30_U32'][0]), 65536)
        self.assertTrue(np.all(result['X16'] == 16384))
        self.assertTrue(np.all(result['norm_S32Q20'] == 1048576))
        gamma[:] *= 2
        doubled = r.rms_oracle(sums, units, gamma, 0, 16*1048576)
        self.assertTrue(np.all(doubled['norm_S32Q20'] == 2097152))

    def test_zero_shortcut_even_with_extreme_scale(self):
        sums = np.zeros((1, 128), np.int64)
        units = np.full(sums.shape, -32000, np.int16)
        gamma, eps, sqrtH = r.constants(np.zeros(128, np.float32), 128)
        result = r.rms_oracle(sums, units, gamma, eps, sqrtH)
        self.assertTrue(all(not v.any() for v in result.values()))

    def test_fraction_mixed_units_reencoding_and_typed_negative(self):
        sums = np.tile(np.array([1, -2], np.int64), 64)[None]
        units = np.tile(np.array([-10, -11], np.int16), 64)[None]
        gamma, eps, sqrtH = r.constants(np.zeros(128, np.float32), 128)
        result = r.rms_oracle(sums, units, gamma, eps, sqrtH)
        self.assertEqual(int(result['row_exponent'][0]), -24)
        np.testing.assert_array_equal(result['X16'][0, :2], [16384, -16384])
        corrupt = {k: v.copy() for k, v in result.items()}
        corrupt['norm_S32Q20'][0, 0] += 1
        with self.assertRaisesRegex(AssertionError, 'independent norm code norm_S32Q20'):
            r.compare_norm(corrupt, result)

    def test_guards_fail_without_clamping(self):
        gamma, eps, sqrtH = r.constants(np.zeros(128, np.float32), 128)
        with self.assertRaisesRegex(OverflowError, 'U64 range'):
            r.rms_oracle(np.ones((1, 128), np.int64), np.full((1, 128), -17, np.int16), gamma, eps, sqrtH)
        with self.assertRaisesRegex(OverflowError, 'signed64'):
            r.rms_oracle(np.full((1, 128), 1 << 62, np.int64),
                         np.tile(np.array([0, -2], np.int16), 64)[None], gamma, eps, sqrtH)
        with self.assertRaisesRegex(OverflowError, 'signed32'):
            r.constants(np.full(128, 3000, np.float32), 128)

    def test_integer_fresh_a8_and_complete_next_partials(self):
        source = np.full((1, 256), 1048576, np.int32)
        a, ae = r.encode_a8(source)
        self.assertTrue(np.all(a == 64))
        self.assertTrue(np.all(ae == -6))
        w, we = np.ones((2, 256), np.int8), np.zeros((2, 2), np.int8)
        stored = {'next.A8': a, 'next.Ae': ae, 'next.parts': np.full((2, 1, 2), 8192, np.int32),
                  'next.units': np.full((2, 1, 2), -6, np.int16), 'next.acc': np.full((1, 2), 16384, np.int64),
                  'next.e0': np.full((1, 2), -6, np.int16), 'next.final_ACT8': np.full((1, 2), 64, np.int8),
                  'next.final_units': np.full((1, 2), 2, np.int16)}
        acc, e0, sat = r.next_oracle(a, ae, w, we, stored, np.array([2, 2], np.int8))
        self.assertEqual(sat, 0)
        self.assertTrue(np.all(r.real(acc, e0) == 256))
        stored['next.parts'][1, 0, 1] += 1
        with self.assertRaisesRegex(AssertionError, 'independent next parts'):
            r.next_oracle(a, ae, w, we, stored, np.array([2, 2], np.int8))

    def test_independent_sqrt_and_rne_certificates(self):
        for value in [1, 2, 15, 16, 17, (1 << 32)-1, (1 << 64)-1]:
            root = math.isqrt(value)
            self.assertLessEqual(root*root, value)
            self.assertGreater((root+1)**2, value)
        self.assertEqual(round(Fraction(5, 2)), 2)
        self.assertEqual(round(Fraction(7, 2)), 4)
        self.assertEqual(round(Fraction(-5, 2)), -2)


if __name__ == '__main__':
    unittest.main()
