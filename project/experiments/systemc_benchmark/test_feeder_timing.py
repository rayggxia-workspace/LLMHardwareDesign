"""Ready/valid acceptance must sample values before the active clock edge."""
from pathlib import Path
import tempfile
import unittest
from feeder_timing_probe import PORTS, vcd_jobs


class PreEdgePackets(unittest.TestCase):
    def test_post_edge_valid_drop_does_not_erase_an_accepted_packet(self):
        with tempfile.TemporaryDirectory() as d:
            ids = {n: chr(65+i) for i, n in enumerate(PORTS)}
            header = '$scope module dut $end\n'+''.join(
                '$var wire 3 %s %s $end\n' % (ids[n], n) for n in PORTS)
            header += '$upscope $end\n$enddefinitions $end\n#0\n'
            state = {n: 0 for n in PORTS};state.update(load_valid=1, load_ready=1, a_ready=1)
            def fields(changes):
                return ''.join('b%d %s\n' % (v, ids[n]) for n, v in changes.items())
            data = header+fields(state)
            for t, changes in [(5, {'clk': 1, 'load_ready': 0}),
                (10, {'clk': 0, 'load_valid': 0, 'a_valid': 1}),
                (15, {'clk': 1, 'a_valid': 0}), (20, {'clk': 0, 'done_valid': 1}),
                (25, {'clk': 1}), (30, {'clk': 0, 'done_take': 1}),
                (35, {'clk': 1, 'done_valid': 0}), (40, {'clk': 0})]:
                data += '#%d\n' % t+fields(changes)
            path = Path(d)/'ports.vcd';path.write_text(data)
            jobs = vcd_jobs(path)
            self.assertEqual([(r['kind'], r['cycle']) for r in jobs[0]],
                             [('L', 0), ('A', 1), ('D', 2), ('T', 3)])


if __name__ == '__main__':
    unittest.main()
