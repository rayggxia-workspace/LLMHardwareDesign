"""Small synthetic layouts/calendars only, no actual model arrays."""
import importlib.util
from pathlib import Path
import unittest
import numpy as np

spec=importlib.util.spec_from_file_location('granite_service76',Path(__file__).with_name('service.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)


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

    def test_scalar_SFU_reserves_shared_lane(self):
        op={'status':'PASS','scalar_dependency_cycles':19,'scratch_peak_bytes':48,'uses_SFU':True,'microprogram_sha256':'a'*64}
        b=m.Builder(128,'M',{'ops':{'udiv_u128':op}});body=[]
        e=b.compute(body,'udiv_u128',3)
        self.assertEqual(e['end'],57)
        self.assertEqual(e['resources'],[{'name':'VR8','start':0,'end':57},{'name':'SFU','start':0,'end':57}])
        self.assertEqual(e['count'],3)


if __name__=='__main__':unittest.main()
