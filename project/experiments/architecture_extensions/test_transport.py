"""Finite-bank and independent COPY calendar boundary tests, no model execution."""
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('transport',Path(__file__).with_name('transport.py'))
t=importlib.util.module_from_spec(spec);spec.loader.exec_module(t)
checker_path=Path(__file__).parents[1]/'range_service'/'receive_service.py'
verify=t.independent_checker(checker_path)


class TransportTests(unittest.TestCase):
    def test_granite_full_returns_rejected(self):
        c=t.certificate('full','V',{'returns':8*1536*4})
        self.assertEqual(c['status'],'REJECT_CAPACITY')
        self.assertEqual(c['required_bytes'],49152)
        c=t.certificate('single','V',{'S64acc':1536*8,'S32return':1536*4})
        self.assertEqual(c['excess_bytes'],2048)

    def test_tiled_metadata_not_free(self):
        c=t.certificate('tile512','V',{'acc':512*8,'return':512*4,'RQ':512*6,'metadata':98})
        self.assertEqual(c['required_bytes'],9314)
        self.assertEqual(c['status'],'FITS_CAPACITY_ONLY')

    def test_falcon_whole_head_not_fit(self):
        for bits in (16,32):
            c=t.certificate('head','R',{'state':128*256*(bits//8)})
            self.assertEqual(c['status'],'REJECT_CAPACITY')
        c=t.aggregate_s_certificate('full32',{'state':32*128*256*4})
        self.assertEqual(c['capacity_bytes'],262144)
        self.assertEqual(c['status'],'REJECT_CAPACITY')

    def test_packet_boundary_header_padding(self):
        g=t.CopyGraph();g.copy('S0','V',1985,[],'explicit logical object packetization')
        self.assertEqual([n['meta']['payload_bytes'] for n in g.nodes],[1984,1])
        self.assertEqual([n['meta']['wire_bytes'] for n in g.nodes],[2016,48])
        for strategy in ('fifo','critical'):
            nodes=t.schedule(g,strategy);t.check_packet_formula(nodes)
            self.assertGreater(verify(nodes,t.capacities())['makespan'],0)

    def test_illegal_bank_object_not_silently_tiled(self):
        g=t.CopyGraph()
        with self.assertRaises(ValueError):
            g.copy('S0','V',49152,[],'cannot fit')
        with self.assertRaises(ValueError):
            g.copy('S0','S0',16,[],'same bank')

    def test_address_bound(self):
        g=t.CopyGraph()
        with self.assertRaises(ValueError):
            g.copy('S0','V',1024,[],'overflow slot',dst_base=16000)

    def test_actual_granite_graph_both_orderings(self):
        for layout in ('roundrobin','all_one'):
            g=t.granite_graph(1536,512,layout)
            for strategy in ('fifo','critical'):
                nodes=t.schedule(g,strategy);t.check_packet_formula(nodes)
                out=verify(nodes,t.capacities())
                self.assertGreaterEqual(out['makespan'],out['lower_bound'])
            payload=sum(n['meta']['payload_bytes'] for n in g.nodes if n['kind']=='packet')
            # Returns stage twice, RQ stage twice, final merged S32 once, metadata once.
            self.assertEqual(payload,2*8*1536*4+2*8*1536*6+1536*4+98)

    def test_falcon_complete_head_copy(self):
        for bits,tile in ((32,8),(16,16)):
            g=t.state_graph(256,128,bits,tile,'roundrobin')
            nodes=t.schedule(g,'critical');t.check_packet_formula(nodes)
            verify(nodes,t.capacities())
            payload=sum(n['meta']['payload_bytes'] for n in nodes if n['kind']=='packet')
            # Four old/proposal transfers and two output-readback transfers, plus descriptor.
            self.assertEqual(payload,6*256*128*(bits//8)+2*(24+(2 if bits==16 else 0)))

    def test_falcon_norm_is_full_scan_then_second_read(self):
        g=t.norm_join_graph(4096,2560,512,'roundrobin')
        nodes=t.schedule(g,'critical');t.check_packet_formula(nodes)
        verify(nodes,t.capacities())
        scans=[n for n in nodes if n['kind']=='local_io' and n['meta']['label'].startswith('global reduction')]
        second=[n for n in nodes if n['kind']=='packet' and n['meta']['label'].startswith('gatednorm x second')]
        self.assertEqual(len(scans),8)
        self.assertGreaterEqual(min(n['start'] for n in second),max(n['end'] for n in scans))

    def test_independent_overlap_negative(self):
        g=t.CopyGraph();g.copy('S0','V',64,[],'a');g.copy('S0','V',64,[],'b')
        nodes=t.schedule(g,'fifo')
        nodes[1]['start']=nodes[0]['start'];nodes[1]['end']=nodes[1]['start']+nodes[1]['duration']
        with self.assertRaises(AssertionError):
            verify(nodes,t.capacities())


if __name__=='__main__':
    unittest.main()
