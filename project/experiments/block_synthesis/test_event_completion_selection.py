import unittest

from benchmark_tile_handoff import binding, hardware, stage, task, window
from run import compile_event_ir


class CompletionSelectionTest(unittest.TestCase):
    def test_executable_search_keeps_alternative_with_an_observable_completion(self):
        services = {
            'early': {'ticks': 10, 'claims': {}, 'phases': [
                {'kind': 'publish', 'ticks': 1, 'claims': {'S': 1}},
                {'kind': 'retire', 'ticks': 9, 'claims': {}}],
                'window_phases': {'write': 'publish', 'publish': 'publish'}},
            'terminal': {'ticks': 6, 'claims': {}, 'hold_claims': {'result': 1}, 'phases': [
                {'kind': 'compute', 'ticks': 5, 'claims': {'M': 1}},
                {'kind': 'publish', 'ticks': 1, 'claims': {'S': 1}}],
                'window_phases': {'write': 'publish', 'publish': 'publish', 'result_hold': 'result'}},
            'consume': {'ticks': 10, 'claims': {'S': 1}},
        }
        arch = hardware({'P0': 16}, ('M', 'S', 'result'), {'out': window('P0', 0, 16)}, {'v': 16}, services)
        fast = binding('early', 'P0', [stage('early', outputs={'out': 'v'})])
        portable = binding('terminal', 'P0', [stage('terminal', outputs={'out': 'v'})])
        consumer = task('consumer', binding('consume', 'P0', [stage('consume', inputs={'out': 'v'})]))
        consumer['event_after'] = [{'task': 'producer', 'from': [0, 'publish'], 'to': [0, 'stage']}]
        model = {'tasks': [task('producer', fast, portable), consumer]}

        timing = compile_event_ir(model, arch, emit_dependencies=True, emit_outputs=False)
        self.assertEqual((timing['plan']['tasks'][0]['binding'], timing['plan']['makespan']), ('early', 11))
        self.assertEqual(len(timing['phase_dependencies']['completion_only_blockers']), 1)

        executable = compile_event_ir(model, arch, emit_dependencies=True, emit_outputs=True)
        self.assertTrue(executable['verification']['passed'])
        self.assertEqual((executable['plan']['tasks'][0]['binding'], executable['plan']['makespan']), ('terminal', 16))
        self.assertEqual(executable['plan']['completion_only_rejections'], 1)
        self.assertEqual(executable['phase_dependencies']['completion_only_blockers'], [])
        mother = executable['outputs']['program']['mother']
        self.assertEqual(mother[1]['wait_for'], [mother[0]['sequence']])
        self.assertEqual(executable['outputs']['program']['source'], executable['outputs']['wiring']['source'])

        sealed = compile_event_ir({'tasks': [task('producer', fast), consumer]}, arch, emit_outputs=True)
        self.assertEqual(sealed['status'], 'no_plan_in_bounded_search')
        self.assertNotIn('outputs', sealed)
        self.assertEqual(sealed['plan']['completion_only_rejections'], 1)
