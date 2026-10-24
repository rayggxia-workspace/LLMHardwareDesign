"""Small synthetic layouts/calendars only, no actual model arrays."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np

spec=importlib.util.spec_from_file_location('granite_service76',Path(__file__).with_name('service.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


def calibration():
    keys=('mul_s32_s32','mul_s64_s32','mul_s32_u16','add_s64','sub_s64','max_s64','add_u128',
        'abs_s64','cmp_s64','align_s32_i64','shl_s64_s128','shl_u128','rne_s64_i32','rne_s128_i32',
        'udiv_u128','isqrt_u128','div_rne_s128_u64_i32','signextend_s16_i64')
    costs={'SIMD8_qualified':False,'frame_capacity_bytes':512,'scratch_peak_bytes':40,
        'scalar_ALU_dependency_cycles':1,'software_controller_dispatches':1,'conservative_scalar_cycles_ALU_plus_dispatch':2,
        'byte_store_reads':2,'byte_store_writes':1,'input_load_bytes':1,'result_read_bytes':1}
    return {'source':{'micro_sha256':'a'*64},'ops':{k:{'costs':dict(costs),'proof':{'kind':'fixed_loops_exhaustive_shift_domain'}} for k in keys}}


def check_ranges(builder):
    def walk(nodes,loops):
        for node in nodes:
            if node['kind']=='loop':
                assert node['end']-node['start']==node['count']*node['period']
                walk(node['body'],loops+[node['count']])
            else:
                assert node.get('FIFO_peak_bytes',0)<=2048
                for a in node.get('accesses',[]):
                    obj=builder.alloc[a['object']]
                    if 'address_class' in a:
                        cls=a['address_class'];assert 0<=cls['minimum']<=cls['maximum']<obj['bytes'];continue
                    strides=a['index_strides'];assert len(strides)<=len(loops)
                    tail=loops[len(loops)-len(strides):] if strides else []
                    end=a['offset']+a['bytes']+(a['repeat']-1)*a['stride']+sum((n-1)*s for n,s in zip(tail,strides))
                    assert 0<=a['offset'] and end<=obj['bytes'],(node['kind'],a,loops,end,obj)
    for e in builder.events:walk(e['body'],[])


class Tests(unittest.TestCase):
    def test_exact_packed_inverse_and_address(self):
        w=(np.arange(2*32*48,dtype=np.int64)%255-127).astype(np.int8).reshape(2,32,48)
        p=m.pack_weight(w);np.testing.assert_array_equal(m.unpack_weight(p),w)
        self.assertEqual(p.shape,(2,2,3,16,16))
        for e,o,k in ((0,0,0),(0,31,47),(1,19,33)):
            self.assertEqual(p[e,o//16,k//16,k%16,o%16],w[e,o,k])
            self.assertEqual(p.reshape(-1)[e*32*48+(o//16)*16*48+k*16+o%16],w[e,o,k])

    def test_pack_rejects_float_and_unaligned(self):
        with self.assertRaises(ValueError):m.pack_weight(np.zeros((2,32,48),np.float32))
        with self.assertRaises(ValueError):m.pack_weight(np.zeros((2,31,48),np.int8))

    def test_packet_offsets_each_packet_and_padding(self):
        c=m.packet_cost(1,15,1986)
        self.assertEqual(c['packets'],2)
        self.assertEqual(c['src_beats'],125+1)
        self.assertEqual(c['dst_beats'],125+2)
        self.assertEqual(c['wire_bytes'],2016+48)

    def test_capacity_full8down_V_rejected(self):
        b=m.Builder(128,'V',{'ops':{}})
        with self.assertRaisesRegex(ValueError,'capacity V'):b.add('all8down','V',8*1536*4)
        self.assertEqual(b.used['V'],0)

    def test_width_fee_unknown_is_rejected(self):
        b=m.Builder(128,'M',{'ops':{}})
        with self.assertRaisesRegex(ValueError,'unknown/unqualified'):b.compute([],'native_mul128')

    def test_scalar_SFU_reserves_shared_lane_and_frame_RMW(self):
        b=m.Builder(128,'M',calibration());m.allocate(b);body=[]
        e=b.compute(body,'udiv_u128',3)
        self.assertEqual(e['end'],72)
        self.assertEqual({r['name'] for r in e['resources']},{'VR8','bank.V','BUS','SFU'})
        self.assertTrue(all(r['start']==0 and r['end']==72 for r in e['resources']))
        self.assertEqual(e['counts']['bank_beats'],21)
        self.assertEqual(e['count'],3)

    def test_fullmerge_fits_with_real_phase_lifetimes(self):
        b=m.Builder(1536,'V',calibration());cap=m.allocate(b)
        self.assertLessEqual(b.used['V'],16384)
        self.assertEqual(b.alloc['down.merge64']['bytes'],12288)
        self.assertEqual(b.alloc['front.gateup']['offset'],b.alloc['down.merge64']['offset'])
        self.assertEqual(b.used['ROM'],131072)
        self.assertEqual(b.alloc['V.byte_regs']['bytes'],40)
        self.assertEqual(b.alloc['V.microframe']['bytes'],512)
        self.assertEqual(cap['owner_physical_RQ_elements'],16)

    def test_lasttoken_complete_pipeline_affine_ranges_and_MACs(self):
        b=m.Builder(1536,'V',calibration());m.allocate(b)
        trace={'expert_input_delta':np.zeros(72,np.int16),'router.ids':np.tile(np.arange(8,dtype=np.uint8),(72,1)),
            'mid_delta':np.zeros((72,8),np.int16)}
        m.front(b,71,trace);m.downstream(b,71,trace);m.nextnorm(b,71)
        check_ranges(b)
        self.assertEqual(b.counts['matrix_S8_MACs'],8*(1024*1536+1536*512))
        self.assertEqual(b.counts['ROM_word32_reads'],8*512)
        phases=[e['meta']['phase'] for e in b.events]
        self.assertEqual(phases,sorted(phases,key={'front':0,'down':1,'norm':2}.get))
        self.assertEqual(b.events[-1]['stage'],'norm.publish_after_complete_consumer')
        self.assertTrue(all(e['meta']['token']==71 for e in b.events))

    def test_large_transfer_is_actual_packet_calendar_not_bulk_FIFO(self):
        b=m.Builder(1536,'V',calibration());m.allocate(b);body=[]
        event=b.transfer(body,'const.gate_up_w8','M.weight',8192)
        cert=event['serial_packet_retiming_certificate']
        self.assertEqual(len(cert['packets']),5)
        self.assertEqual(sum(p['payload_bytes'] for p in cert['packets']),8192)
        self.assertEqual(cert['packets'][0]['start'],0)
        self.assertEqual(cert['packets'][-1]['end'],event['end'])
        self.assertEqual(len({r['name'] for r in event['resources']}),len(event['resources']))
        self.assertTrue(all(r['start']==0 and r['end']==event['end'] for r in event['resources']))
        self.assertLessEqual(max(p['FIFO_peak_bytes'] for p in cert['packets']),2048)
        self.assertTrue(all(p['payload_bytes']<=1984 for p in cert['packets']))
        other=[];source_unaligned=b.transfer(other,'cut.norm','M.weight',1984,1,0)
        self.assertEqual(source_unaligned['FIFO_peak_bytes'],2032)
        with self.assertRaisesRegex(ValueError,'engine caller staging'):b.engine([], 'M.weight',0,8192)

    def test_partial_write_has_endpoint_RMW_and_fits_FIFO(self):
        self.assertEqual(m.partial_write_beats(0,16),0)
        self.assertEqual(m.partial_write_beats(15,2),2)
        b=m.Builder(128,'M',calibration());m.allocate(b);body=[]
        e=b.transfer(body,'cut.norm','V.x32',2,0,15)
        self.assertEqual(e['counts']['dst_rmw_beats'],2)
        self.assertEqual(e['FIFO_peak_bytes'],80)



if __name__=='__main__':unittest.main()
