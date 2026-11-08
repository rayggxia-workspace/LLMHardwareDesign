import tempfile
from pathlib import Path
import unittest
from analyze_activity import normalize_vcd


class ActivityInterval(unittest.TestCase):
    VCD = ('$timescale 1ps $end\n$scope module dut $end\n'
           '$scope module block_v2_m $end\n$var wire 1 ! clk $end\n'
           '$upscope $end\n$upscope $end\n$enddefinitions $end\n'
           '#100\n0!\n#105\n1!\n#110\n0!\n')

    def test_remove_warmup_offset_without_changing_activity(self):
        with tempfile.TemporaryDirectory() as d:
            src, dst = Path(d) / 'input.vcd', Path(d) / 'output.vcd'
            src.write_text(self.VCD)
            r = normalize_vcd(src, dst, 10, 'dut/block_v2_m')
            self.assertEqual(r['source_first_ps'], 100)
            self.assertEqual(dst.read_text().split('$enddefinitions $end\n')[1],
                             '#0\n0!\n#5\n1!\n#10\n0!\n')

    def test_wrong_scope_and_window_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            src, dst = Path(d) / 'input.vcd', Path(d) / 'output.vcd'
            src.write_text(self.VCD)
            with self.assertRaisesRegex(ValueError, 'scope absent'):
                normalize_vcd(src, dst, 10, 'TOP/dut')
            with self.assertRaisesRegex(ValueError, 'interval differs'):
                normalize_vcd(src, dst, 11, 'dut/block_v2_m')


if __name__ == '__main__':
    unittest.main()
