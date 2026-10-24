import importlib.util
import io
from pathlib import Path
import random
import unittest
import math

S = importlib.util.spec_from_file_location('byte_micro76', Path(__file__).with_name('micro.py'))
M = importlib.util.module_from_spec(S); S.loader.exec_module(M)


def rne(n, d):
    q, r = divmod(abs(n), d)
    q += 2*r > d or (2*r == d and q&1)
    return -q if n < 0 else q


class TinyByteTests(unittest.TestCase):
    def test_byte_alu_carries_signed_multiply_and_shifts(self):
        self.assertEqual(M.alu('ADD', 255, 255, 1), (255, 1))
        self.assertEqual(M.alu('SUB', 0, 255, 1), (0, 1))
        self.assertEqual(M.alu('MULS8', 128, 128), (0, 64))
        self.assertEqual(M.alu('SHL', 255, 8), (0, 0))
        with self.assertRaises(ValueError): M.alu('ADD', 256)

    def test_full_signed_digit_boundary_products(self):
        for op, aa, bb, products in [('mul_s32_s32', -(1<<31), (1<<31)-1, 25),
                                     ('mul_s64_s32', -(1<<63), -(1<<31), 45),
                                     ('mul_s32_u16', -(1<<31), 32768, 15),
                                     ('mul_s32_u16', (1<<31)-1, 65535, 15)]:
            result, profile = M.execute(op, aa, bb)
            self.assertEqual(result, {'value': aa*bb, 'valid': True})
            self.assertEqual(profile['primitive_counts']['MULS8'], products)
            self.assertLessEqual(profile['scratch_peak_bytes'], M.FRAME_BYTES)

    def test_signed_add_and_unsigned_add_reject_overflow(self):
        for op, a, b in [('add_s64', (1<<63)-1, 1), ('add_s64', -(1<<63), -1), ('add_u128', (1<<128)-1, 1)]:
            r, _ = M.execute(op, a, b); self.assertFalse(r['valid'])
        r, _ = M.execute('add_s64', -321, 100); self.assertEqual(r['value'], -221); self.assertTrue(r['valid'])

    def test_rne_negative_ties_zero_and_cast_guard(self):
        for a, shift in [(-5, 1), (-3, 1), (5, 1), (3, 1), (0, 0), (-(1<<63), 64), ((1<<31)-1, 0), (1<<31, 0), (-(1<<127), 128)]:
            op = 'rne_s128_i32' if a < -(1<<63) else 'rne_s64_i32'
            r, _ = M.execute(op, a, shift=shift); expected = rne(a, 1<<shift)
            self.assertEqual(r['value'], expected)
            self.assertEqual(r['valid'], -(1<<31) <= expected < 1<<31)

    def test_S16_scale_sign_extension(self):
        for value in (-(1<<15), -1, 0, (1<<15)-1):
            result, profile = M.execute('signextend_s16_i64', value)
            self.assertEqual(result, {'value': value, 'valid': True})
            self.assertEqual(profile['scalar_ALU_dependency_cycles'], 10)

    def test_shift_inverse_guards_full_domain(self):
        for op, a, shift, width in [('align_s32_i64', -(1<<31), 32, 64),
                                     ('align_s32_i64', 1, 63, 64),
                                     ('shl_s64_s128', -(1<<63), 12, 128),
                                     ('shl_u128', (1<<127), 1, 128)]:
            r, _ = M.execute(op, a, shift=shift); value = a << shift
            signed = op != 'shl_u128'; valid = (-(1<<(width-1)) <= value < 1<<(width-1)) if signed else 0 <= value < 1<<width
            self.assertEqual(r['valid'], valid)
            if valid: self.assertEqual(r['value'], value)

    def test_restoring_division_and_zero_divisor(self):
        for a, b in [(0, 1), ((1<<128)-1, (1<<64)+1), (17, 3), (123, 0)]:
            r, p = M.execute('udiv_u128', a, b)
            self.assertEqual(r['valid'], b != 0)
            if b: self.assertEqual((r['quotient'], r['remainder']), divmod(a, b))
            self.assertFalse(p['SIMD8_qualified'])

    def test_restoring_isqrt_full_u128(self):
        for a in [0, 1, 2, (1<<128)-1, ((1<<63)+7)**2-1]:
            r, _ = M.execute('isqrt_u128', a); self.assertEqual(r['value'], math.isqrt(a))

    def test_arbitrary_divisor_rne_and_norm_cast_guard(self):
        for n, d in [(-5, 2), (-3, 2), (123456789<<12, 777), (1<<100, 1), (0, 0)]:
            r, _ = M.execute('div_rne_s128_u64_i32', n, d)
            if d:
                expect = rne(n, d); self.assertEqual(r['value'], expect)
                self.assertEqual(r['valid'], -(1<<31) <= expect < 1<<31)
            else: self.assertFalse(r['valid'])

    def test_subtract_and_maximum_selection(self):
        for a, b in [(-(1<<63), 1), ((1<<63)-1, -1), (-5, 7), (5, 5)]:
            result, _ = M.execute('sub_s64', a, b)
            value = a-b; valid = -(1<<63) <= value < 1<<63
            self.assertEqual(result['valid'], valid)
            if valid: self.assertEqual(result['value'], value)
            result, _ = M.execute('max_s64', a, b)
            self.assertEqual(result, {'value': max(a, b), 'valid': True})

    def test_compare_abs_and_finite_live_store(self):
        for a, b in [(-(1<<63), (1<<63)-1), (-1, 0), (1, 1)]:
            r, _ = M.execute('cmp_s64', a, b); self.assertEqual(r, {'less': a < b, 'equal': a == b, 'valid': True})
            r, _ = M.execute('abs_s64', a); self.assertEqual(r['value'], abs(a))
        m = M.Machine(); x = m.alloc('x', 1)
        with self.assertRaisesRegex(ValueError, 'uninitialized'): m.op('COPY', x[0])
        with self.assertRaises(MemoryError): m.alloc('too_big', 513)

    def test_trace_carries_addresses_and_actual_step_counts(self):
        stream = io.StringIO(); result, p = M.execute('mul_s32_u16', -17, 32768, stream=stream)
        lines = stream.getvalue().splitlines()
        self.assertEqual(sum(x.startswith('A ') for x in lines), p['scalar_ALU_dependency_cycles'])
        self.assertEqual(result['value'], -17*32768)
        self.assertTrue(any(x.startswith('M ') for x in lines))
        self.assertTrue(any(x.startswith('F ') for x in lines))

    def test_rne_program_counts_fixed_across_shift_control_domain(self):
        profiles = [M.execute('rne_s64_i32', -12345, shift=s)[1]['primitive_counts'] for s in (0, 1, 7, 8, 31, 63, 64, 128)]
        self.assertTrue(all(p == profiles[0] for p in profiles))


if __name__ == '__main__': unittest.main()
