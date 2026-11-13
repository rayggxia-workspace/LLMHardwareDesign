"""Regression for participant-local finite-loop external memory admission."""
import unittest

from event_physical_contract import qualify_hardware


class LoopMemoryTest(unittest.TestCase):
    def test_each_participant_needs_its_own_directional_path(self):
        endpoints = {}
        nets = {}

        def add_bundle(name, signals):
            nets[name] = {'signals': []}
            for role, source, target, width in signals:
                suffix = '/{bit}' if width > 1 else ''
                driver = f'{source}/{name}/{role}/out' + suffix
                sink = f'{target}/{name}/{role}/in' + suffix
                for bit in range(width):
                    for template, owner, kind in ((driver, source, 'driver'), (sink, target, 'sink')):
                        pin = template.format(bit=bit)
                        endpoints[pin] = {'assembly': owner, 'role': kind, 'native_net': pin}
                nets[name]['signals'].append({'name': role, 'width': width,
                                              'driver': driver, 'sinks': [sink]})

        def path(name, source, target):
            add_bundle(name, [('data', source, target, 8), ('valid', source, target, 1),
                              ('ready', target, source, 1), ('ack', target, source, 1)])
            return {'nets': [name], 'abi': 'ready-valid-commit', 'external_owner': 'memory', 'width_bits': 8}

        for control in ('first', 'second'):
            add_bundle(control, [('command', 'mother', control, 1), ('done', control, 'mother', 1)])
        load = path('load', 'memory', 'first')
        store = path('store', 'second', 'memory')
        traffic = {'A': {'read': {'bytes': 16, 'path': load}},
                   'B': {'write': {'bytes': 32, 'path': None}}}
        service = {'nets': ['load', 'store'], 'read_bytes': 16, 'write_bytes': 32,
                   'memory_by_site': traffic, 'finite_loop': {'io_site': 'A',
                       'participants': {'A': {'control': 'first'}, 'B': {'control': 'second'}},
                       'completion': 'native_loop_final_ack'}}
        hardware = {'nets': nets, 'control_groups': {'first': {'site': 'A', 'control_net': 'first'},
                                                    'second': {'site': 'B', 'control_net': 'second'}},
                    'event_model': {'routes': {}, 'services': {'loop': service}}}

        def qualify():
            return qualify_hardware(hardware, {'endpoints': endpoints})['event_model']

        self.assertEqual(qualify()['physical_interface_issues']['services']['loop'],
                         'second: missing finite-loop memory write interface')
        traffic['B']['write']['path'] = load
        self.assertIn('second: finite-loop memory write: missing or ambiguous physical roles',
                      qualify()['physical_interface_issues']['services']['loop'])
        traffic['B']['write']['path'] = store
        result = qualify()
        self.assertEqual(result['physical_interface_issues']['services'], {})
        self.assertEqual(result['services']['loop']['nets'], ['first', 'load', 'second', 'store'])
        self.assertIn('missing physical service route inventory', result['native_dispatch_issues']['services']['loop'])
        service['write_bytes'] += 16
        self.assertEqual(qualify()['physical_interface_issues']['services']['loop'],
                         'finite-loop memory traffic does not match service totals')
