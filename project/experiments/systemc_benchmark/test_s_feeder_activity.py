"""Never hide a physically connected activity bit when comparing initializations."""
import tempfile
from pathlib import Path
import unittest
from s_feeder_activity import unused_debug_bits, vcd_parts


class PhysicalTraceBits(unittest.TestCase):
    def fixture(self, root):
        names = {'feeder.p_row': 3, 'feeder.queue_row[0]': 3,
                 'feeder.queue_row[1]': 3, '$auto$alumacc.cc:548:replace_alu$1113.P': 2}
        net = root/'physical.v'
        net.write_text(''.join('wire [%d:0] %s%s ;\nCELL c%d (.Q(%s%s [%d]));\n' %
            (w-1, chr(92), n, i, chr(92), n, w-1) for i, (n, w) in enumerate(names.items())))
        header = ''.join('$var wire %d %s %s $end\n' % (w, chr(65+i), n)
                         for i, (n, w) in enumerate(names.items()))+'$enddefinitions $end\n#0\n'
        return net, header, names

    def test_only_unconnected_low_bits_are_ignored_in_comparison(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d);net, header, names = self.fixture(root)
            proof = unused_debug_bits(net)
            a, b = root/'a.vcd', root/'b.vcd'
            a.write_text(header+''.join('b%s %s\n' % ('0'*w, chr(65+i)) for i, w in enumerate(names.values())))
            b.write_text(header+''.join('b0%s %s\n' % ('1'*(w-1), chr(65+i)) for i, w in enumerate(names.values())))
            self.assertNotEqual(vcd_parts(a, proof)[1], vcd_parts(b, proof)[1])
            self.assertEqual(vcd_parts(a, proof)[2], vcd_parts(b, proof)[2])
            changed = b.read_text().replace('b011 A', 'b111 A')
            b.write_text(changed)
            self.assertNotEqual(vcd_parts(a, proof)[2], vcd_parts(b, proof)[2])

    def test_any_physical_reference_to_a_low_bit_rejects_the_proof(self):
        with tempfile.TemporaryDirectory() as d:
            net, _, _ = self.fixture(Path(d))
            net.write_text(net.read_text()+r'CELL extra (.D(\feeder.p_row [0]));'+'\n')
            with self.assertRaisesRegex(ValueError, 'physical reference'):
                unused_debug_bits(net)


if __name__ == '__main__':
    unittest.main()
