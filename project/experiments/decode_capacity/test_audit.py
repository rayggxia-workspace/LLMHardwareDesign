from copy import deepcopy
import hashlib
import json
from pathlib import Path
import unittest

from audit import audit, crosscheck_graph, dense_work, m_contract


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent


class TestCapacity(unittest.TestCase):
    def setUp(self):
        self.inventory = json.loads((HERE/'inventory.json').read_text())
        self.workloads = json.loads((HERE/'workloads.json').read_text())

    def test_exported_graph_matches_official_3b_shape_count(self):
        proof = json.loads((ROOT/'work/YUZE-LU/236/graph-dense-check.json').read_text())
        config = json.loads((HERE/'configs/Qwen2.5-3B.json').read_text())
        work = dense_work(config)
        self.assertEqual(work['products_per_token'], 3_085_697_024)
        self.assertTrue(crosscheck_graph(proof, work)['passed'])
        for invalid in (0, -1, True):
            with self.assertRaises(ValueError):
                crosscheck_graph({**proof, 'tokens': invalid}, work)
        proof['static_weight_dot_shapes'][0]['K'] += 1
        with self.assertRaisesRegex(ValueError, 'differs from exported'):
            crosscheck_graph(proof, work)

    def test_qwen3_uses_explicit_head_dim_and_full_vocabulary(self):
        config = json.loads((HERE/'configs/Qwen3-4B.json').read_text())
        work = dense_work(config)
        self.assertEqual(work['effective_query_dimension'], 4096)
        self.assertEqual(work['effective_kv_dimension'], 1024)
        self.assertEqual(work['products_per_token'], 4_022_272_000)
        # An independently expanded list of the seven matrix shapes.
        matrices = [(2560,4096),(2560,1024),(2560,1024),(4096,2560),
                    (2560,9728),(2560,9728),(9728,2560)]
        self.assertEqual(work['products_per_token'], 36*sum(a*b for a,b in matrices)+2560*151936)

    def test_capacity_is_optimistic_and_does_not_claim_system_tokens(self):
        result = audit(ROOT, self.inventory, self.workloads)
        self.assertEqual(result['optimistic_S8_products_per_second'], 57_600_000_000)
        row = result['workloads'][1]
        self.assertAlmostEqual(row['optimistic_dense_compute_token_s_upper_bound'], 14.320264765784113)
        self.assertFalse(row['dense_capacity_necessary_condition_met'])
        self.assertEqual(row['minimum_equivalent_M_count'], 16)
        required = 72.5*4_022_272_000
        self.assertLess(15*64*300_000_000, required)
        self.assertGreaterEqual(16*64*300_000_000, required)
        self.assertEqual(row['ideal_4bit_weight_bandwidth_bytes_per_s'], 145_807_360_000)
        self.assertIn('not_system_simulation', result['kind'])

    def test_added_hardware_and_duplicate_instances_are_rejected(self):
        for duplicate in (True, False):
            inventory = deepcopy(self.inventory)
            engine = deepcopy(inventory['engines'][0])
            if not duplicate:
                engine['id'] = 'invented.M'
            inventory['engines'].append(engine)
            with self.assertRaises(ValueError):
                audit(ROOT, inventory, self.workloads)

    def test_rtl_hash_and_structural_contract_drift_fail_closed(self):
        engine = self.inventory['engines'][0]
        raw = (ROOT/engine['rtl_path']).read_bytes()
        self.assertEqual(m_contract(raw, engine['rtl_sha256'])['optimistic_products_per_cycle'], 64)
        with self.assertRaisesRegex(ValueError, 'hash changed'):
            m_contract(raw+b'\n', engine['rtl_sha256'])
        bad = raw.replace(b'i<64;i=i+1)product[i]', b'i<32;i=i+1)product[i]')
        with self.assertRaisesRegex(ValueError, 'differs'):
            m_contract(bad, hashlib.sha256(bad).hexdigest())
        inventory = deepcopy(self.inventory)
        inventory['engines'][0]['products_per_cycle'] = 512
        with self.assertRaisesRegex(ValueError, 'declared products'):
            audit(ROOT, inventory, self.workloads)

    def test_unsupported_models_or_invalid_dimensions_do_not_get_bounds(self):
        original = json.loads((HERE/'configs/Qwen3-4B.json').read_text())
        for fields in ({'model_type':'qwen3_moe'}, {'num_experts':8}, {'head_dim':0},
                       {'num_key_value_heads':3}, {'hidden_size':True}, {'hidden_act':'gelu'}):
            with self.assertRaises(ValueError):
                dense_work({**original, **fields})


if __name__ == '__main__':
    unittest.main()
