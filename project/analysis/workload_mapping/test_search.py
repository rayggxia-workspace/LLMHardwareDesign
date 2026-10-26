"""Research checks: independent ledger, exact optimum, tampering and semantics."""
import copy
from fractions import Fraction
import random
import unittest

from project.analysis.workload_mapping.search import Hardware, Infeasible, exact, solve, wire
from project.analysis.workload_mapping.search_model import transformer, trap, Workload
from project.analysis.workload_mapping.search_check import replay, export


def micro(seed):
    r=random.Random(seed)
    w=Workload("micro"+str(seed),dict(evidence="synthetic exhaustive fixture"))
    weights=[w.initial("w"+str(i),(n,),"weight") for i,n in enumerate([640,384,256])]
    outputs=[]
    for j in range(6):
        reads=[r.choice(weights)]
        if j>=2:reads.append(outputs[j-2])
        outputs.append(w.add("t"+str(j),"gemm_complete_rq",reads,(64,),pool="matrix"))
    return w.freeze()


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.w=transformer(8,2,1,4,4,True)
        self.h=Hardware(capacity=1024,vector_capacity=1024)

    def test_all_methods_independent_packet_and_capacity_audit(self):
        for method in ("fixed","greedy","beam"):
            r=solve(self.w,self.h,method,width=3,depth=2,frontier=4)
            actual=replay(self.w,self.h,r)
            literal=replay(self.w,self.h,r,False)
            self.assertEqual(actual,literal)
            self.assertEqual(actual['functional_dag_sha256'],self.w.digest())

    def test_exhaustive_optimum_and_beam_gaps_are_real(self):
        for seed in range(12):
            w=micro(seed);h=Hardware(capacity=1024,matrices=1)
            optimum=exact(w,h)
            for method in ("fixed","greedy","beam"):
                r=solve(w,h,method,width=4,depth=3,frontier=6)
                self.assertGreaterEqual(r['wire_bytes'],optimum)
                replay(w,h,r,False)

    def test_public_contract_roundtrip_for_every_algorithm(self):
        for method in ("fixed","greedy","beam"):
            r=solve(self.w,self.h,method,width=3,depth=2,frontier=4)
            g,b,m=export(self.w,self.h,r)
            self.assertEqual(sum(x['transport']['wire_bytes'] for x in m['mapping_request']['communication']),r['wire_bytes'])
            self.assertEqual(m['summary']['logical']['status'],'pass')

    def test_tampered_loads_rejected(self):
        r=solve(self.w,self.h);r['plan'][0]['loads']=[]
        with self.assertRaisesRegex(ValueError,'load'):replay(self.w,self.h,r)

    def test_tampered_peak_rejected(self):
        r=solve(self.w,self.h);r['plan'][0]['peak_bytes']=0
        with self.assertRaisesRegex(ValueError,'capacity'):replay(self.w,self.h,r)

    def test_duplicate_task_rejected(self):
        r=solve(self.w,self.h);r['plan'].append(r['plan'][0])
        with self.assertRaisesRegex(ValueError,'duplicate'):replay(self.w,self.h,r)

    def test_early_consumer_rejected(self):
        r=solve(self.w,self.h);r['plan'][0]['task']=len(self.w.tasks)-1
        with self.assertRaisesRegex(ValueError,'premature'):replay(self.w,self.h,r)

    def test_wrong_pool_rejected(self):
        r=solve(self.w,self.h);r['plan'][0]['resource']='unknown'
        with self.assertRaisesRegex(ValueError,'placement'):replay(self.w,self.h,r)

    def test_fake_traffic_total_rejected(self):
        r=solve(self.w,self.h);r['wire_bytes']-=128
        with self.assertRaisesRegex(ValueError,'ledger'):replay(self.w,self.h,r)

    def test_incomplete_plan_rejected(self):
        r=solve(self.w,self.h);r['plan'].pop()
        with self.assertRaisesRegex(ValueError,'incomplete'):replay(self.w,self.h,r)

    def test_small_capacity_is_not_silently_legal(self):
        with self.assertRaises(Infeasible):solve(self.w,Hardware(capacity=32,vector_capacity=32))

    def test_fifo_cannot_borrow_private_ram(self):
        with self.assertRaises(ValueError):Hardware(fifo_bytes=128)

    def test_packet_boundary_uses_original_estimator(self):
        self.assertEqual([wire(x) for x in [8,1984,1985,3968]],[128,2048,2176,4096])

    def test_deterministic_plan_without_timing(self):
        a=solve(self.w,self.h,'beam',width=3,depth=2,frontier=4)
        b=solve(self.w,self.h,'beam',width=3,depth=2,frontier=4)
        a.pop('algorithm_seconds');b.pop('algorithm_seconds')
        self.assertEqual(a,b)

    def test_decode_has_all_prefill_and_previous_token_dependencies(self):
        decoded=[(i,t) for i,t in enumerate(self.w.tasks) if t.phase=='decode']
        first=decoded[0][1]
        self.assertEqual(len(first.dependencies),2) # 8 prefill tokens / tile4
        last0=max(i for i,t in decoded if t.id.startswith('s8_'))
        token1=next(t for i,t in decoded if t.id.startswith('s9_'))
        self.assertIn(last0,token1.dependencies)

    def test_kv_history_reaches_decode_and_is_not_reset(self):
        task=next(t for t in self.w.tasks if t.id=='s9_L0_attention_h0')
        keys=[v for v in task.reads if 'ropek' in v]
        self.assertEqual(len(keys),4) # two prefill tiles and two decode tokens

    def test_weight_identity_shared_across_steps_not_layers(self):
        w=transformer(8,2,2,4,4,True)
        weights=[v for v in w.values.values() if v.role=='weight']
        one=[v for v in self.w.values.values() if v.role=='weight']
        self.assertEqual(len(weights),2*len(one))
        self.assertGreater(len(w.users['W_L0_q_0']),1)

    def test_tiling_does_not_change_linear_macs(self):
        def count(w):return sum(t.macs for t in w.tasks if t.op=='gemm_complete_rq')
        self.assertEqual(count(transformer(16,2,1,4,4,True)),count(transformer(16,2,1,8,2,True)))

    def test_full_k_accumulation_before_single_rq_numeric_oracle(self):
        # Tile loops and whole dot products use different loop orders; apply
        # exact Fraction/round only AFTER all K contributions have arrived.
        rng=random.Random(761)
        x=[[rng.randrange(-8,8) for _ in range(7)] for _ in range(5)]
        weight=[[rng.randrange(-8,8) for _ in range(6)] for _ in range(7)]
        expected=[[max(-128,min(127,round(Fraction(sum(a*b for a,b in zip(row,col)),2))))
                   for col in zip(*weight)] for row in x]
        for rt,nt,kt in [(1,2,3),(2,4,2),(4,3,7)]:
            actual=[[0]*6 for _ in x]
            for r in range(0,5,rt):
                for c in range(0,6,nt):
                    for start in range(0,7,kt):
                        for i in range(r,min(r+rt,5)):
                            for j in range(c,min(c+nt,6)):
                                for k in range(start,min(start+kt,7)):
                                    actual[i][j]+=x[i][k]*weight[k][j]
            actual=[[max(-128,min(127,round(Fraction(v,2)))) for v in row] for row in actual]
            self.assertEqual(actual,expected)

    def test_no_search_invented_hardware_or_time_claim(self):
        r=solve(self.w,self.h);proof=replay(self.w,self.h,r)
        self.assertIsNone(proof['end_to_end_seconds'])
        self.assertFalse(proof['physical_qualified'])
        self.assertEqual(len(proof['peak_ram_bytes']),3)


if __name__=='__main__':unittest.main()
