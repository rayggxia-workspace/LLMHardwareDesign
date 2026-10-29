"""Failure controls for new routed-graph and sparse external bus boundaries."""
import tempfile
from pathlib import Path
import unittest
from interconnect_experiment import fixture
from interconnect_spef import prepare,wrapper
from linkclose_measure import paths


class ClosureControls(unittest.TestCase):
    def test_real_receiver_fanout_keeps_all_native_boundaries(self):
        with tempfile.TemporaryDirectory()as temporary:
            out=Path(temporary);native,links=fixture(out/'inputs',vector=True)
            native['extra']=dict(native['right'])
            link=dict(links[0],extra_sinks=[['extra','d[0]']])
            meta=prepare(native,out/'prepared',[link]);text=wrapper(meta,native,'direct')
            self.assertIn('extra:d[0]',meta['selected'])
            self.assertIn('fixture_right u_extra',text)
            self.assertIn('.d({extra_d[1], f000})',text)
            self.assertIn('.d({right_d[1], f000})',text)
            from interconnect_spef import link_spef
            with self.assertRaises(AssertionError):link_spef(meta,out/'bad.spef','direct',100)

    def test_two_native_landings_and_via_disconnection(self):
        source='NETS 1 ;\n- n ( a p ) ( b p ) + ROUTED metal10 ( 10 10 ) BV1_via10 NEW metal11 ( 10 10 ) ( 110 * ) BV1_via11 NEW metal12 ( 110 10 ) ( * 210 ) BV1_via11 NEW metal11 ( 110 210 ) BV1_via10 ;\nEND NETS'
        graph=paths(source)['n']
        self.assertEqual(sum(e['via']is not None for e in graph),4)
        self.assertAlmostEqual(sum(e['length_um']for e in graph),.15)
        self.assertEqual({tuple(e[k])for e in graph for k in ('a','b')if e[k][0]=='metal10'},
                         {('metal10',10,10),('metal10',110,210)})
        with self.assertRaises(AssertionError):paths(source.replace('( 110 * ) BV1_via11','( 110 * )',1))

    def test_nonzero_external_vector_keeps_literal_bit_identity(self):
        with tempfile.TemporaryDirectory()as temporary:
            out=Path(temporary);native,links=fixture(out/'inputs',vector=True)
            # Only bit0 is consumed internally; external bit1 stays a real
            # one-bit vector [1:1], never an escaped scalar or invented bit0.
            meta=prepare(native,out/'prepared',links[:1])
            text=wrapper(meta,native,'direct')
            self.assertIn('input [1:1] right_d;',text)
            self.assertIn('output [1:1] left_q;',text)
            self.assertIn('.d({right_d[1], f000})',text)
            self.assertNotIn('\\right_d[1]',text)


if __name__=='__main__':unittest.main()
