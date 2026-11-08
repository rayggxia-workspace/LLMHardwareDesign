from copy import deepcopy
import unittest
from unittest.mock import patch

from recompile_ir import recompile
from primitive_stages import lower
from test_nexp_contract import fixture
from verify_primitive_cost import verify


class TestRecompile(unittest.TestCase):
    def test_historical_nexp_relowered_without_reusing_costs(self):
        for staged in (False,True):
            old=fixture()
            old['primitive_program']['value_bindings']={'y':'exp'}
            if staged:lower(old)
            # Historical IR has the correct vector semantics but the wrong
            # native loop. Recompile the vector program, not the old costs.
            old['program'][0]['body']={'repeat':4,'body':{'sequence':[{'call':name} for name in
                ('n_soft_begin','n_soft_stats','n_soft_finalize','n_exp')]}}
            old['native_call_abi'].pop('nexp')
            frozen=deepcopy(old)
            with patch('streaming_ir.duration',return_value=1),patch('verify_primitive_cost.duration',return_value=1):
                new=recompile(old)
                self.assertTrue(verify(new)['passed'])
            self.assertEqual(old,frozen)
            self.assertEqual(new['primitive_program'],old['primitive_program'])
            self.assertEqual(new['hardware']['resources'],old['hardware']['resources'])
            self.assertEqual(new['tasks'][0]['bindings'][0]['external_read_words'],12)

    def test_missing_saved_type_fails_instead_of_guessing_exponent(self):
        old=fixture();old['primitive_program']['value_bindings']={'y':'exp'}
        del old['primitive_program']['instructions'][0]['exponent']
        with self.assertRaisesRegex(ValueError,'typed format'):recompile(old)

    def test_legacy_static_column_scope_preserves_its_action_family(self):
        from test_dot_cache import example
        from preparation_reuse import lower as prepare
        from primitive_stages import lower as stages
        from dot_cache import variants as cache
        from column_shards import variants_for as columns
        from phased_compounds import variants_for as phases
        old=example()
        for task in old['tasks']:task['bindings']=[b for b in task['bindings'] if 'read_cache' not in b]
        old.pop('read_cache_scope')
        old['primitive_program']['value_bindings']={'out':'v'}
        with patch('streaming_ir.duration',return_value=1),patch('verify_primitive_cost.duration',return_value=1):
            prepare(old);stages(old);cache(old,state_cost=True);columns(old,dynamic=False);phases(old)
            scope=old['column_shard_scope'];scope['max_bindings_per_task']=scope.pop('max_static_bindings_per_task')
            scope.pop('frontier_partition_bindings')
            new=recompile(old)
        self.assertEqual(new['column_shard_scope']['frontier_partition_bindings'],0)
        self.assertEqual([len(t['bindings']) for t in new['tasks']],[len(t['bindings']) for t in old['tasks']])
        self.assertEqual(new['hardware']['resources'],old['hardware']['resources'])


if __name__=='__main__':unittest.main()
