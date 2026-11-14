import unittest

from tlm_model_registry import ModelBinding
from tlm_plan_preflight import match_models


class EffectiveModelTest(unittest.TestCase):
    def test_matching_uses_effective_service_and_completion(self):
        original = dict(target=3, schema=3, abi=7, opcode=4, completion='destination_commit_ack', calls=1)
        old_key = (3, 3, 7, 4, 'destination_commit_ack')
        new_key = (3, 1, 26411009, 260, 'destination_commit_ack')
        rewrite = {old_key: dict(schema=1, abi=26411009, opcode=260)}
        providers = [dict(group='U0', signature=original, status='candidate_native_route')]
        model = ModelBinding(lambda: None, 'fixture-gather@1')
        for rejected_key in (old_key, (*new_key[:-1], 'service_done')):
            absent, = match_models(providers, rewrite, {rejected_key: model})
            self.assertEqual(absent['status'], 'missing_tlm_model')
        matched, = match_models(providers, rewrite, {new_key: model})
        self.assertEqual(matched['status'], 'model_available')
        self.assertEqual(matched['model_identity'], model.identity)
        self.assertEqual(matched['effective_signature']['opcode'], 260)

    def test_model_cannot_override_missing_hardware(self):
        key = (1, 2, 3, 4, 'service_done')
        signed = dict(target=1, schema=2, abi=3, opcode=4, completion='service_done', calls=1)
        model = ModelBinding(lambda: None, 'fixture-scope@1')
        for status in ('missing_native_dispatch', 'missing_completion_provider'):
            result, = match_models([dict(group='P1', signature=signed, status=status)], {}, {key: model})
            self.assertEqual(result['status'], status)
            self.assertNotIn('model_identity', result)


if __name__ == '__main__':
    unittest.main()
