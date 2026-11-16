from copy import deepcopy
import unittest
from unittest.mock import patch

from loop_dp import search
from materialized_tiles import variants_for
from test_tile_bindings import fixture,variants_for as register_tiles
from tile_accounting import charge,traffic
from verify_loop_dp import verify
from verify_primitive_cost import verify as verify_cost


class TestMaterializedTiles(unittest.TestCase):
    def fixture(self,**kwargs):
        ir,q=fixture(**kwargs);register_tiles(ir,q);variants_for(ir);return ir

    def audit(self,ir):
        with patch('verify_primitive_cost.duration',return_value=1):return verify_cost(ir)

    def test_shared_pool_real_memory_and_independent_cost(self):
        ir,q=fixture(columns=11);register_tiles(ir,q)
        old={t['id']:deepcopy(t['bindings']) for t in ir['tasks']};old_bytes=ir['required_external_bytes']
        variants_for(ir);self.audit(ir)
        self.assertGreater(ir['materialized_tile_scope']['added_bindings'],0)
        self.assertGreater(ir['required_external_bytes'],old_bytes)
        for task in ir['tasks']:
            self.assertEqual(task['bindings'][:len(old[task['id']])],old[task['id']])
            for b in task['bindings']:
                if 'materialized_tile' not in b:continue
                self.assertEqual(sum(charge(b,ir['hardware']).values()),b['ticks']);traffic(b)
                self.assertEqual(b['tile_work']['initial_zero_loads'],32)
                self.assertEqual(b['tile_work']['temporary_external_words'],2*b['tile_work']['packed_outputs'])
        with self.assertRaises(ValueError):variants_for(ir)

    def test_selected_materialized_plan_both_widths(self):
        ir=self.fixture(columns=11);self.audit(ir)
        for task in ir['tasks']:
            selected=[b for b in task['bindings'] if 'materialized_tile' in b]
            if selected:task['bindings']=selected
        for width in (1,8):
            p=search(ir['tasks'],ir['hardware'],width=width);result=verify(ir['tasks'],ir['hardware'],p)
            self.assertGreater(result['window_audit']['materialized_tasks'],0)
            bad=deepcopy(p);row=next(r for r in bad['tasks'] if ';materialized' in r['binding'])
            resource=next(k for k,v in row['resource_windows'].items() if v[0]>row['start'])
            row['resource_windows'][resource][0]-=1
            with self.assertRaisesRegex(ValueError,'resource windows differ'):verify(ir['tasks'],ir['hardware'],bad)

    def test_forged_phase_traffic_region_and_zero_refill_rejected(self):
        base=self.fixture(columns=11)
        mutations=[lambda b:b['materialized_tile']['phases'][0].update(ticks=1),
            lambda b:b['materialized_tile']['resource_offsets'].clear(),
            lambda b:b['tile_work'].update(initial_zero_loads=16),
            lambda b:b['tile_work'].update(external_read_words=b['tile_work']['external_read_words']-16),
            lambda b:b['materialized_tile']['external_region'].update(words=1),
            lambda b:b.update(ticks=b['ticks']-1)]
        for mutate in mutations:
            ir=deepcopy(base);b=next(b for t in ir['tasks'] for b in t['bindings'] if 'materialized_tile' in b)
            mutate(b)
            with self.assertRaises(ValueError):self.audit(ir)

    def test_capacity_rejects_new_action_without_dropping_old(self):
        ir,q=fixture(columns=11);register_tiles(ir,q)
        ir['hardware']['external_capacity_words']=ir['required_external_bytes']//16
        old=deepcopy(ir['tasks']);variants_for(ir)
        self.assertEqual(ir['tasks'],old);self.assertEqual(ir['materialized_tile_scope']['added_bindings'],0)
        self.audit(ir)

    def test_resource_and_price_bounds_respect_short_auxiliary_claims(self):
        from net_tail import ConditionalTail
        from work_price import WorkPriceBound
        from types import SimpleNamespace
        ir=self.fixture(columns=11)
        task=next(t for t in ir['tasks'] if any('materialized_tile' in b for b in t['bindings']))
        b=next(b for b in task['bindings'] if 'materialized_tile' in b)
        task={**task,'after':[],'bindings':[b]};h=ir['hardware']
        ctx=ConditionalTail([task],h,{task['id']:[]},[task['id']])
        price=WorkPriceBound(ctx,[task],h)
        e_resource=b['macro_binding']['E']+'.E';lo,hi=b['materialized_tile']['resource_offsets'][e_resource]
        state=SimpleNamespace(done=0,nets=frozenset(),makespan=lo,
            resources={r:(0,)*n for r,n in h['resources'].items()},windows={e_resource:((0,lo),)})
        # E is occupied until this Dot naturally reaches its E phase: no delay.
        self.assertEqual(ctx.ready_finish(task['id'],state.nets,state.resources,0,windows=state.windows),b['ticks'])
        self.assertLessEqual(price.get(state),b['ticks'])
        state.windows={e_resource:((lo,hi),)};state.makespan=hi
        self.assertEqual(ctx.ready_finish(task['id'],state.nets,state.resources,0,windows=state.windows),b['ticks']+hi-lo)
