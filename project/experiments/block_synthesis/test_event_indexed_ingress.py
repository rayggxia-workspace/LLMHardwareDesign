"""Exercise an indexed native ingress sharing a full SRAM window with a later load."""
from copy import deepcopy
import unittest

from run import compile_event_graph
from test_event_execution import hardware


class IndexedIngressTest(unittest.TestCase):
    def test_ingress_byte_address_and_full_window_lifetime(self):
        arch = hardware()
        spec = arch['event_model']
        table_format = {'bits': 32, 'lanes': 4, 'exponent': -16}
        raw = {'shape': [1, 4], 'dtype': 'INT32', 'format': table_format}
        gamma = {'shape': [4], 'dtype': 'INT32'}
        graph = {'inputs': ['index', 'gamma'], 'weights': ['table'], 'outputs': ['y'],
                 'values': {'index': {'shape': [1], 'dtype': 'INT32'}, 'gamma': gamma,
                            'table': {'shape': [2, 4], 'dtype': 'INT32', 'format': table_format},
                            'x': raw, 'y': raw},
                 'tasks': [
                     {'id': 'embed', 'op': 'Gather', 'inputs': ['table', 'index'], 'outputs': ['x']},
                     {'id': 'update', 'op': 'Update', 'inputs': ['x', 'gamma'], 'outputs': ['y']},
                 ]}
        spec.update(initial_copies={'other': 'index'}, initial_backing=['gamma', 'table'],
                    external_alignment_bytes=16, indexed_gather=[{
                        'id': 'indexed', 'site': 'P0', 'index_window': 'other', 'index_window_offset': 4,
                        'output_window': 'source', 'address_bits': 32, 'bytes_per_tick': 8,
                        'setup_per_index': 1, 'claims': {'S0': 1},
                    }], recipes=[{
                        'op': 'Update', 'inputs': [raw, gamma], 'outputs': [raw],
                        'binding': {'id': 'update', 'site': 'P0', 'event_stages': [{
                            'service': 'produce', 'inputs': {'source': 'in:0', 'other': 'in:1'},
                            'outputs': {'other': 'out:0'}, 'inplace_windows': ['other'],
                        }]},
                    }])
        spec['services']['produce']['inplace_windows'] = {'other': 16}
        result = compile_event_graph(graph, arch)
        self.assertEqual(result['status'], 'planned')
        self.assertTrue(result['verification']['passed'])
        program = result['outputs']['program']
        self.assertEqual([row['wait_for'] for row in program['mother']],
                         [[], [0], [0, 1], [0, 1, 2]])
        gather, load, _ = program['locals']['P0']
        self.assertEqual((gather['read'][0]['address'], gather['read'][0]['bytes']), (20, 4))
        self.assertEqual((load['write'][0]['address'], load['write'][0]['bytes']), (16, 16))

        overwritten = deepcopy(graph)
        overwritten['tasks'].insert(0, {'id': 'early', 'op': 'Early',
                                        'inputs': ['gamma'], 'outputs': ['early']})
        overwritten['values']['early'] = gamma
        altered = deepcopy(arch)
        altered['event_model']['recipes'].append({
            'op': 'Early', 'inputs': [gamma], 'outputs': [gamma],
            'binding': {'id': 'early', 'site': 'P0', 'event_stages': [{
                'service': 'block-source', 'inputs': {'source': 'in:0'}, 'outputs': {'other': 'out:0'},
            }]},
        })
        plan = compile_event_graph(overwritten, altered)
        self.assertEqual(plan['status'], 'planned')
        self.assertEqual(plan['plan']['tasks'][0]['id'], 'embed')
        self.assertNotIn('index', [event.get('value') for row in plan['plan']['tasks']
                                   for event in row['evaluation']['events']])
        spec['indexed_gather'][0]['index_window_offset'] = 2
        self.assertIn('aligned index', compile_event_graph(graph, arch)['reason'])
