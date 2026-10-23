"""Known-resource/input-semantic regressions for this model adaptation."""
import unittest
from service_model import build,audit_schedule


class Contract(unittest.TestCase):
    def test_input_capacity_and_retile(self):
        with self.assertRaises(ValueError):build(16,8192,'static','near',1,1,8)
        g=build(8,8192,'static','near',1,1,8)
        sources={}
        for p in g.packets:
            if p['src'].startswith('S'):
                sources.setdefault(p['kind'],set()).add(p['src'])
        self.assertFalse(sources['W8']&sources['A8'])
        self.assertFalse(sources['META']&(sources['A8']|sources['W8']))
        for p in g.packets:
            if p['dst'].startswith('S'):
                self.assertEqual(g.nodes[p['write']]['port'],p['dst'])
        audit_schedule(g,g.schedule('critical'))

    def test_decode_packet_granularity(self):
        for k in (2048,8192):
            a=build(1,k,'static','near',1,2,8)
            b=build(1,k,'static','shared',1,2,8)
            self.assertEqual(a.bytes['wire_ACT8'],b.bytes['wire_ACC32'])

    def test_early_rounding_counterexample(self):
        from fractions import Fraction
        self.assertEqual(round(Fraction(1+1,2)),1)
        self.assertEqual(round(Fraction(1,2))+round(Fraction(1,2)),0)


if __name__=='__main__':unittest.main()
