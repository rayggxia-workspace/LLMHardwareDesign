from copy import deepcopy
import unittest
from unittest.mock import patch

import numpy as np

from dot_cache_replay import DotCache
from loop_dp import search
from phase_accounting import account as phase_account
from search_diagnostics import bounds
from selected_order_profile import profile
from test_tile_bindings import fixture,variants_for as register_tiles
from tile_partitions import variants_for
from traffic_accounting import account as traffic_account
from utilization import report
from verify_loop_dp import verify
from verify_primitive_cost import verify as verify_cost
from wide_program import execute


def example(columns=17,*,two_e=False,k=5,phased=False,shared=False):
    ir,q=fixture(columns=columns,k=k,shared=shared)
    if two_e:
        h=ir['hardware'];meta=deepcopy(h['leaf_inventory']['vector'])
        meta.update(site='second_vector.S',io_resource='second_vector.S.IO',memory_group=1)
        h['leaf_inventory']['second_vector']=meta;h['sites'][meta['site']]=deepcopy(h['sites']['vector.S'])
        for field in ('resources','nets'):
            for name,value in list(h[field].items()):
                if name.startswith('vector.'):h[field]['second_vector'+name[len('vector'):]]=deepcopy(value)
    register_tiles(ir,q);variants_for(ir,phased=phased)
    return ir


class TestTilePartitions(unittest.TestCase):
    def audit(self,ir):
        with patch('verify_primitive_cost.duration',return_value=1):return verify_cost(ir)

    def test_old_pool_unchanged_and_native_column_cost_audit(self):
        ir,q=fixture(columns=17);register_tiles(ir,q)
        old=deepcopy(ir['tasks']);size=ir['required_external_bytes'];variants_for(ir)
        self.assertGreater(ir['tile_partition_scope']['added_bindings'],0)
        self.assertEqual(ir['required_external_bytes'],size)
        for a,b in zip(old,ir['tasks']):self.assertEqual(b['bindings'][:len(a['bindings'])],a['bindings'])
        self.audit(ir)
        with self.assertRaises(ValueError):variants_for(ir)

    def test_selected_partition_cost_schedule_and_numerical_replay(self):
        ir=example(two_e=True);self.audit(ir)
        for task in ir['tasks']:
            selected=[b for b in task['bindings'] if 'tile_partition' in b]
            if selected:task['bindings']=selected
        for width in (1,8):
            p=search(ir['tasks'],ir['hardware'],width=width);verify(ir['tasks'],ir['hardware'],p)
            with patch('verify_primitive_cost.duration',return_value=1):
                moved=traffic_account(ir,p);parts=phase_account(ir,p);occupancy=report(ir,p)
            self.assertEqual(moved['total_logical_words'],p['external_words'])
            self.assertLessEqual(bounds(ir['tasks'],ir['hardware'],p)['completion_lower_bound'],p['makespan'])
            self.assertLessEqual(profile(ir['tasks'],ir['hardware'],p)['selected_order_relaxed_lower_bound'],p['makespan'])
            self.assertEqual(sum(parts['serial_components'].values()),occupancy['serial_work'])
            rng=np.random.default_rng(123)
            a=rng.integers(-(1<<31),1<<31,size=(2,5),dtype=np.int64)
            b=rng.integers(-32768,32768,size=(5,17),dtype=np.int64)
            cache=DotCache(ir,p)
            actual=execute(ir['primitive_program'],{'a':a,'b':b},[[1,2]],None,dot_executor=cache)
            shift=ir['primitive_program']['instructions'][0]['attributes']['shift']
            from full_integer import round_shift
            expected=np.clip(round_shift(a@b,shift),-(1<<31),(1<<31)-1)
            np.testing.assert_array_equal(actual['out'].raw,expected)
            self.assertGreater(cache.report()['tile_calls'],1)

    def test_both_multi_column_children_execute_tails_and_final_rounding(self):
        from full_integer import round_shift
        rng=np.random.default_rng(220103)
        for columns,k,shift in ((17,5,0),(19,7,8),(24,17,24)):
            ir=example(columns,two_e=True,k=k)
            node=ir['primitive_program']['instructions'][0]
            # This test exercises the arithmetic data path with a different
            # legal final shift; native cost audits use the unchanged fixture.
            selected=next(b for b in ir['tasks'][-1]['bindings'] if 'tile_partition' in b and
                all(c['binding']['dot_tile']['tile'][1]>1 for c in b['parallel_shards']['children']))
            ir['tasks'][-1]['bindings']=[selected]
            node['attributes']['shift']=shift
            for c in selected['parallel_shards']['children']:c['binding']['dot_tile']['final_shift']=shift
            p=search(ir['tasks'],ir['hardware'],width=1);verify(ir['tasks'],ir['hardware'],p)
            a=rng.integers(-(1<<31),1<<31,size=(2,k),dtype=np.int64)
            a[0,:3]=[-2147483648,-32769,2147483647]
            b=rng.integers(-32768,32768,size=(k,columns),dtype=np.int64)
            cache=DotCache(ir,p)
            result=execute(ir['primitive_program'],{'a':a,'b':b},[[1,2]],None,dot_executor=cache)
            np.testing.assert_array_equal(result['out'].raw,np.clip(round_shift(a@b,shift),-(1<<31),(1<<31)-1))
            r=cache.report();self.assertEqual(r['tile_calls'],2)
            self.assertTrue(all(e['counts']['scatter_executes']>0 for e in r['tile_events']))

    def test_coverage_address_temporary_and_resources_cannot_be_forged(self):
        base=example()
        mutations=[lambda b:b['parallel_shards']['children'][0]['columns'].__setitem__(0,1),
            lambda b:b['parallel_shards']['children'][0]['binding']['tile_column_view'].update(external_row_stride_words=1),
            lambda b:b['parallel_shards']['children'][0]['binding']['tile_work'].update(ticks=1),
            lambda b:b['parallel_shards']['children'][1]['binding']['dot_tile']['temporary_external_region'].update(
                b['parallel_shards']['children'][0]['binding']['dot_tile']['temporary_external_region']),
            lambda b:b.update(external_read_words=b['external_read_words']-1),
            lambda b:b['parallel_shards']['children'][1]['binding']['resources'].append(
                b['parallel_shards']['children'][0]['binding']['resources'][0])]
        for mutate in mutations:
            ir=deepcopy(base);b=next(b for t in ir['tasks'] for b in t['bindings'] if 'tile_partition' in b)
            mutate(b)
            with self.assertRaises(ValueError):self.audit(ir)

    def test_shared_channels_are_not_invented_parallelism(self):
        ir,q=fixture(columns=17,shared=True)
        register_tiles(ir,q)
        variants_for(ir)
        self.assertEqual(ir['tile_partition_scope']['added_bindings'],0)
        self.audit(ir)


if __name__=='__main__':unittest.main()
