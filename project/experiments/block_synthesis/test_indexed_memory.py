from copy import deepcopy
import unittest

from indexed_memory import index_address
from numeric import Format, pack, unpack
from quantization import quantize
from run import compile_model
from solver import Unsupported
from test_leaf_lowering import fixture


def embedding_model():
    f={'bits':16,'exponent':-10,'lanes':2}
    return {'tasks':[{'id':'embed','op':'Gather','inputs':['table','ids'],
                      'outputs':['embedding'],'numeric':'INT16','attributes':{}}],
            'values':{'table':{'shape':[7,8],'format':deepcopy(f)},
                      'ids':{'shape':[1,2],'dtype':'INT64'},
                      'embedding':{'shape':[1,2,8],'format':deepcopy(f)}},
            'outputs':['embedding'],'weights':['table']}


class TestIndexedMemory(unittest.TestCase):
    def test_index_bounds_negative_indices_and_overflow(self):
        self.assertEqual(index_address(-1,7,4,1,1,40),25*16)
        self.assertEqual(index_address(-7,7,4,0,1,40),0)
        for index in (-8,7,1.5,True):
            with self.assertRaises(ValueError):index_address(index,7,4,0,1,40)
        with self.assertRaises(ValueError):index_address(0,7,4,4,1,40)
        with self.assertRaises(ValueError):index_address(6,7,4,0,1,8)

    def test_indexed_load_scheduling_capacity_traffic_and_manifest(self):
        m=embedding_model(); h=fixture(); before=deepcopy((m,h))
        h['sites']={'P0.S':h['sites']['P0.S']}
        before=deepcopy((m,h))
        result=compile_model(m,h,seconds=.1,rounds=0,cover_limit=1)
        self.assertEqual((m,h),before)
        self.assertEqual(result['status'],'planned')
        self.assertTrue(result['verification']['passed'])
        self.assertEqual(len(result['graph']['tasks']),8)
        # Eight indexed table reads, two index-record loads, eight output stores.
        self.assertEqual(result['plan']['external_words'],18)
        regions=result['outputs']['program_ir']['external_regions']
        self.assertEqual(next(r['words'] for r in regions if r['value']=='table'),28)
        services=[r for r in result['outputs']['program_ir']['requests'] if r['kind']=='service']
        self.assertTrue(all('table_base_address_words' in r['native_program'][0] for r in services))
        self.assertFalse(any(s.get('address_generation_timing_qualified',True) for s in
            result['resolved_hardware']['services'].values() if s['op']=='IndexedGather'))
        h['external_capacity_words']=27
        self.assertEqual(compile_model(m,h,seconds=.1,rounds=0,cover_limit=1)['status'],'no_verified_plan')

    def test_gather_does_not_implicitly_quantize_float(self):
        m=embedding_model(); del m['values']['table']['format']
        with self.assertRaisesRegex(Unsupported,'format missing'):compile_model(m,fixture())

    def test_int64_index_records_are_lossless(self):
        f=Format(64,0,1)
        values=[-(1<<63),(1<<63)-1,-1,0]
        self.assertEqual(unpack(pack(values,f),f,len(values)),values)

    def test_actual_quantization_and_error_receipt(self):
        import numpy as np
        raw,report=quantize([.5,1.5,2.5,-.5,-1.5],exponent=0)
        self.assertEqual(raw.tolist(),[0,2,2,0,-2])
        self.assertEqual(report['clipped_elements'],0)
        values=np.array([-10.,0.,20.])
        raw,report=quantize(values)
        self.assertLessEqual(report['max_abs_error'],2.**(report['format']['exponent']-1))
        self.assertEqual(report['clipped_elements'],0)
        self.assertTrue(np.array_equal(values,[-10.,0.,20.]))
        for invalid in ([float('inf')],[float('nan')],[]):
            with self.assertRaises(ValueError):quantize(invalid)


if __name__=='__main__':unittest.main()
