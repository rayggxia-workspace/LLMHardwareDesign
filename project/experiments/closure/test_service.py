"""Small synthetic calendars only; complete service runs belong on server."""
import importlib.util
from pathlib import Path
import unittest
import math

spec=importlib.util.spec_from_file_location('closure_service',Path(__file__).with_name('service.py'))
s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s)


def bounds(builder,nodes,loops=()):
    for n in nodes:
        if n['kind']=='loop':bounds(builder,n['body'],loops+(n['count'],))
        else:
            for a in n.get('accesses',[]):
                if 'address_class' in a:continue
                strides=a.get('index_strides',[])
                if len(strides)>len(loops):raise AssertionError('stride depth')
                strides=[0]*(len(loops)-len(strides))+strides
                last=a['offset']+sum((count-1)*stride for count,stride in zip(loops,strides))
                last+=(a.get('repeat',1)-1)*a.get('stride',0)+a['bytes']
                if last>builder.alloc[a['object']]['bytes']:raise AssertionError((a['object'],last,builder.alloc[a['object']]['bytes']))


class ServiceTests(unittest.TestCase):
    def test_unaligned_each_packet(self):
        c=s.packet_cost(1,15,1985)
        self.assertEqual(c['packets'],2)
        self.assertEqual(c['src_beats'],s.beats(1,1984)+s.beats(1985,1))
        self.assertEqual(c['dst_beats'],s.beats(15,1984)+s.beats(1999,1))
        self.assertEqual(c['wire_bytes'],32+1984+32+16)

    def test_fixed_capacity_and_spill(self):
        a=s.Builder('r32_d8');b=s.Builder('v16_d2');c=s.Builder('r32_d16_spill')
        self.assertEqual(a.used['R'],32768)
        self.assertEqual(b.used['V'],14336)
        self.assertEqual(c.used['S0'],32768)
        self.assertEqual(c.used['R'],24576)
        self.assertEqual(a.inventory['matrix']['S8_PEs'],256)
        self.assertEqual(a.inventory['lanes']['S8_lanes'],8)
        with self.assertRaises(ValueError):a.add('extra','R',1)

    def test_full_K_synthetic_matrix(self):
        b=s.Builder('r32_d8')
        for key,n in (('ext.w',16*512),('ext.a',512),('ext.y',64),('ext.m',64),('ext.e',32),('ext.bias',64)):b.add(key,'EXT',n)
        b.matrix('test',16,512,'ext.w',('ext.m','ext.e'),'ext.bias','ext.a','ext.y',0)
        bounds(b,b.events[0]['body'])
        self.assertEqual(b.totals['matrix_mac'],16*512)
        self.assertTrue(b.events[0]['meta']['complete_K_before_RQ'])
        self.assertEqual(b.totals['copy_byte'],8192)

    def test_stream_tail_affine_bounds(self):
        b=s.Builder('v16_d2')
        for key in ('ext.x','ext.y','const.g'):b.add(key,'EXT',1056*4)
        b.stream('synthetic',1056,[('ext.x',0),('const.g',0)],[('ext.y',0)],{'mul32':lambda n:n},0)
        bounds(b,b.events[0]['body'])
        self.assertEqual(b.totals['mul32'],1056)

    def test_ROM_payload_fourbyte_alignment(self):
        b=s.Builder('r32_d8')
        b.add('silu','ROM',65540);b.add('dt','ROM',2097280);b.add('alpha','ROM',2097280)
        self.assertEqual(b.used['ROM'],4260100)

    def test_FIFO_padding_and_split_label_not_scheduler_input(self):
        b=s.Builder('r32_d8');b.add('x','EXT',16)
        body=[];b.transfer(body,'x','local.Raux',2)
        self.assertEqual(body[0]['FIFO_peak_bytes'],48)
        self.assertNotIn('label',b.__dict__)

    def test_bytewise_wide_cost_and_single_SFU(self):
        b=s.Builder('v16_d2');body=[]
        b.compute(body,{'mul32':8,'rne64':8,'division_iterations':128,'isqrt_iterations':64})
        self.assertEqual(body[0]['resources'][0]['name'],'VR8')
        self.assertEqual(body[0]['resources'][0]['end'],25+24*10+10)
        self.assertEqual([r['name'] for r in body[0]['resources'][1:]],['SFU','SFU'])

if __name__=='__main__':unittest.main()
