from copy import deepcopy
from collections import Counter
import random
import unittest
from unittest.mock import patch

from traffic_accounting import cached_reads, account
from test_column_shards import fixture, compound
from loop_dp import optimize


class TestTrafficAccounting(unittest.TestCase):
    def test_cover_decisions_are_checked_before_compound_traffic_expansion(self):
        from cover_frontier import search
        ir = fixture()
        ir['resident_actions'] = []
        ir['model']['weights'] = ['b']
        next(t for t in ir['tasks'] if t['id']=='v')['bindings'] = [compound(ir)]
        plan = search(ir['tasks'], ir['hardware'], width=2)
        # No resident actions are registered in this compound-only fixture.
        with patch('verify_primitive_cost.duration', return_value=1), patch(
                'verify_resident_bindings.verify', return_value={'passed':True}):
            result = account(ir, plan)
            self.assertEqual(result['total_logical_words'], plan['external_words'])
            self.assertEqual(result['cached_Dot_services'], 2)
            self.assertTrue(result['cover_audit']['passed'])
            bad = deepcopy(plan);bad['tasks'][0]['covers'] = []
            with self.assertRaisesRegex(ValueError, 'membership'):
                account(ir, bad)

    def test_operand_counts_against_explicit_access_trace(self):
        for seed in range(150):
            rng = random.Random(seed)
            r,n,k = [rng.randint(1,7) for _ in range(3)]
            ca,cb = [rng.choice((1,3)) for _ in range(2)]
            t = rng.randint(0,k); h = rng.randint(0,t)
            c = dict(rows=r,columns=n,K=k,components=[ca,cb],stripe=t,cost_model='dot-prefix-state-v2')
            actual,_ = cached_reads(c, {'evaluation':{'reused_prefix':h}}, immutable_weight=True)
            expected = Counter(zero_packet=1)
            for row in range(r):
                for kk in range(h,t):
                    for a in range(ca):expected['A_prefix_fill'] += 1
                for col in range(n):
                    for kk in range(k):
                        for b in range(cb):expected['B_immutable_weights'] += 1
                        for a in range(ca):
                            for b in range(cb):
                                if kk >= t:expected['A_streamed_reloads'] += 1
            self.assertEqual(Counter(actual), expected)

    def test_selected_compounds_conserve_traffic_and_reject_invalid_plan(self):
        ir = fixture()
        ir['model']['weights'] = ['b']
        next(t for t in ir['tasks'] if t['id']=='v')['bindings'] = [compound(ir)]
        plan = optimize(ir['tasks'],ir['hardware'])
        with patch('verify_primitive_cost.duration',return_value=1):
            result = account(ir,plan)
        self.assertEqual(result['total_logical_words'],plan['external_words'])
        self.assertEqual(result['cached_Dot_services'],2)
        self.assertEqual(result['logical_scalar_record_words']['B_immutable_weights'],2*9*5)
        self.assertEqual(result['nominal_record_bytes'],16*plan['external_words'])
        bad = deepcopy(plan);bad['external_words'] -= 1
        with patch('verify_primitive_cost.duration',return_value=1), self.assertRaises(ValueError):
            account(ir,bad)


if __name__ == '__main__':
    unittest.main()
