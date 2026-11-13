from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from cover_frontier import search
from publish_event_handoff import build, source_identity
from route_contract import elaborate
from test_event_execution import binding, hardware, stage, task


ROUTER = Path(os.environ.get('LLMHARDWARE_UPPER_ROUTER', Path(__file__).resolve().parents[1] / 'upper_router'))
if (ROUTER / 'adapter.py').is_file():
    sys.path.append(str(ROUTER))
    import_path = list(sys.path)
    try:
        from adapter import bind_request
        from handoff import verify_handoff
        from search import route
    finally:
        sys.path[:] = import_path


def fixture():
    model = {'tasks': [
        task('a', binding('producer', stage('produce', outputs={'source': 'x'}))),
        task('b', binding('consumer', stage('consume', inputs={'input': 'x'}, outputs={'result': 'y'})),
             after=('a',)),
    ]}
    arch = hardware()
    arch['program_target'] = {
        'topology_id': 'arbitrary-topology',
        'controllers': {'head': {'level': 'mother', 'abi': 'master-v1', 'capacity_bytes': 16},
                        'lane0': {'level': 'local', 'abi': 'local-v1', 'capacity_bytes': 16}},
    }
    arch['nets']['resident-control'] = {'cost': 0, 'fixed': True}
    plan = search(model['tasks'], arch)
    catalog = {'schema_version': 'route-contract/1', 'demands': {}}
    for name, suffix in [('P0-P1', 'open'), ('resident-control', 'fixed')]:
        catalog['demands'][name] = {'signals': [
            {'name': suffix, 'width': 1, 'driver': suffix + '-out', 'sinks': [suffix + '-in']}
        ]}
    base = {'schema_version': 'route-contract/1', 'base_id': 'independent', 'state': 'candidate',
            'dbu_per_micron': 2000, 'views': {kind: {'path': kind, 'sha256': 'a'*64}
                                            for kind in ('odb', 'netlist', 'gds')}, 'endpoints': {},
            'fixed_native_nets': {'native-fixed': {'driver': 'fixed-out', 'sinks': ['fixed-in']}}}
    for name, x, y, role in [('open-out', 20, 30, 'driver'), ('open-in', 180, 30, 'sink'),
                             ('fixed-out', 20, 60, 'driver'), ('fixed-in', 180, 60, 'sink')]:
        base['endpoints'][name] = {'odb_term': name, 'role': role,
                                  'native_net': 'native-fixed' if name.startswith('fixed') else name,
                                  'm10_shapes': [{'layer': 'M10', 'object': name,
                                                  'rect_dbu': [x-2, y-2, x+2, y+2]}]}
    via = {'cut': 2, 'spacing': 3, 'lower_enclosure': 1, 'upper_enclosure': 1}
    rules = {'technology': {'bounds': [0, 0, 220, 120], 'origin': [0, 0], 'pitch': 10,
                            'width': 2, 'spacing': 2, 'via10': via.copy(), 'via11': via.copy()}}
    return model, arch, plan, catalog, base, rules


class RouteAdmissionTest(unittest.TestCase):
    def test_missing_route_endpoint_is_rejected_during_search(self):
        from run import compile_event_ir

        model, arch, _, catalog, base, _ = fixture()
        for name, route in arch['event_model']['routes'].items():
            if 'DDR' in (route['src'], route['dst']):
                route['nets'] = [name]
                arch['nets'][name] = {'cost': 1}
        result = compile_event_ir(model, arch, route_base=base, route_catalog=catalog,
                                  route_scope='interface')
        self.assertEqual(result['status'], 'planned')
        del base['endpoints']['open-in']
        result = compile_event_ir(model, arch, route_base=base, route_catalog=catalog,
                                  route_scope='interface')
        self.assertEqual(result['status'], 'no_plan_in_bounded_search')

    def test_native_service_requires_matching_assembly_inventory(self):
        _, _, _, catalog, base, _ = fixture()
        views = {key: key for key in base['views']}
        catalog['demands']['local-read'] = {'realization': {'kind': 'native_service', 'id': 'read'}}
        base['assemblies'] = [{'id': 'P0', 'views': views, 'inventory_sha256': 'b'*64}]
        base['leaf_instances'] = [{'instance': 'P0/memory'}]
        base['realizations'] = {'read': {'kind': 'native_service', 'assembly': 'P0',
                                         'views': views, 'inventory_sha256': 'b'*64,
                                         'leaf_instances': ['P0/memory']}}
        request = elaborate({'local-read': []}, catalog, base, {})
        self.assertEqual(request['status'], 'endpoint_binding_complete')
        self.assertEqual(request['realizations'][0]['provider_id'], 'read')
        self.assertEqual(request['nets'], [])
        base['realizations']['read']['inventory_sha256'] = 'c'*64
        with self.assertRaisesRegex(ValueError, 'inventory mismatch'):
            elaborate({'local-read': []}, catalog, base, {})


@unittest.skipUnless((ROUTER / 'adapter.py').is_file(), 'upper router checkout required')
class HandoffTest(unittest.TestCase):
    def test_replay_plan_reaches_router_with_its_own_control_waits(self):
        from run import compile_event_graph

        _, arch, _, catalog, base, rules = fixture()
        fmt = {'shape': [8], 'dtype': 'INT16'}
        graph = {'inputs': [], 'outputs': ['y'], 'values': {'x': fmt, 'y': fmt}, 'tasks': [
            {'id': 'a', 'op': 'Produce', 'inputs': [], 'outputs': ['x']},
            {'id': 'b', 'op': 'Consume', 'inputs': ['x'], 'outputs': ['y']},
        ]}
        arch['event_model'].update(timing='replay', recipes=[
            {'op': 'Produce', 'inputs': [], 'outputs': [fmt],
             'binding': binding('producer', stage('produce', outputs={'source': 'out:0'}))},
            {'op': 'Consume', 'inputs': [fmt], 'outputs': [fmt],
             'binding': binding('consumer', stage('consume', inputs={'input': 'in:0'},
                                                  outputs={'result': 'out:0'}))},
        ])
        result = compile_event_graph(graph, arch)
        pack = build(result['event_ir'], result['resolved_hardware'], result['plan'],
                     catalog, base, rules, bind_request)
        self.assertEqual(pack['program']['control_ir']['mother'][2]['wait_for'], [0, 1])
        self.assertEqual(pack['handoff']['source']['plan_sha256'],
                         result['outputs']['program']['source']['plan_sha256'])
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            for name, contents in pack.items():
                (folder / (name + '.json')).write_text(json.dumps(contents), encoding='utf-8')
            self.assertEqual(verify_handoff(pack['algorithm2-input'], folder)['scope'], 'interface')
            self.assertEqual(route(pack['algorithm2-input'])['failed'], {})

    def test_actual_algo2_consumer_routes_exact_selected_move_and_fixed_wiring(self):
        inputs = fixture()
        pack = build(*inputs, bind_request)
        self.assertEqual(pack['wiring']['users']['P0-P1'], [{'task_id': 'b', 'binding_id': 'consumer', 'event_id': 1}])
        self.assertEqual(pack['wiring']['users']['resident-control'], [])
        self.assertEqual(pack['handoff']['coverage']['static_bit_members'], 2)
        self.assertEqual(pack['handoff']['coverage']['new_signal_nets'], 1)
        self.assertEqual(pack['program']['kind'], 'scheduled_event_ir')
        self.assertFalse(pack['program']['native_execution_qualified'])
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            for name, contents in pack.items():
                (folder / (name+'.json')).write_text(json.dumps(contents), encoding='utf-8')
            accepted = verify_handoff(pack['algorithm2-input'], folder)
            self.assertEqual(accepted['scope'], 'interface')
            self.assertEqual(route(pack['algorithm2-input'])['failed'], {})
            pack['program']['decisions'][0]['binding'] = 'tampered'
            (folder/'program.json').write_text(json.dumps(pack['program']), encoding='utf-8')
            with self.assertRaisesRegex(ValueError, 'fingerprint'):
                verify_handoff(pack['algorithm2-input'], folder)

    def test_tampered_plan_and_missing_endpoint_are_rejected(self):
        model, arch, plan, catalog, base, rules = fixture()
        corrupt = {**plan, 'nets': []}
        with self.assertRaisesRegex(ValueError, 'summary'):
            build(model, arch, corrupt, catalog, base, rules, bind_request)
        incomplete = deepcopy(base)
        del incomplete['endpoints']['open-in']
        with self.assertRaisesRegex(ValueError, 'unbound physical demands'):
            build(model, arch, plan, catalog, incomplete, rules, bind_request)
        del catalog['demands']['P0-P1']
        with self.assertRaisesRegex(ValueError, 'missing_interface_template'):
            build(model, arch, plan, catalog, base, rules, bind_request)

    def test_product_requires_frozen_base_and_complete_source_bound_real_bytes(self):
        model, arch, plan, catalog, base, rules = fixture()
        args = (model, arch, plan, catalog, base, rules, bind_request)
        with self.assertRaisesRegex(ValueError, 'frozen native views'):
            build(*args, route_scope='product')
        base['state'] = 'frozen'
        with self.assertRaisesRegex(ValueError, 'all native physical views'):
            build(*args, route_scope='product')
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name in ('odb', 'def', 'gds', 'netlist', 'spef'):
                view = root / name
                view.write_bytes(name.encode())
                base['views'][name] = {'path': str(view), 'sha256': hashlib.sha256(view.read_bytes()).hexdigest()}
            manifest = {'schema_version': 'algo1-control-images/1', 'source': source_identity(model, arch, plan),
                        'topology_id': 'arbitrary-topology', 'images': []}
            for controller, level, abi in [('head', 'mother', 'master-v1'), ('lane0', 'local', 'local-v1')]:
                image = root / (controller + '.bin')
                image.write_bytes(controller.encode())
                manifest['images'].append({'controller': controller, 'level': level, 'abi': abi,
                                          'path': image.name, 'bytes': image.stat().st_size,
                                          'sha256': hashlib.sha256(image.read_bytes()).hexdigest()})
            def publish(data):
                return build(*args, route_scope='product', manifest=data, artifact_root=root)
            with self.assertRaisesRegex(ValueError, 'source-bound control images'):
                build(*args, route_scope='product')
            with self.assertRaisesRegex(ValueError, 'incomplete'):
                publish({**manifest, 'images': manifest['images'][:1]})
            with self.assertRaisesRegex(ValueError, 'different schedule'):
                publish({**manifest, 'source': {}})
            output = publish(manifest)
            self.assertEqual(output['handoff']['coverage']['control_images'], 2)
            self.assertEqual([bytes.fromhex(i['payload_hex']) for i in output['program']['images']],
                             [b'head', b'lane0'])
            (root/'lane0.bin').write_bytes(b'wrong')
            with self.assertRaisesRegex(ValueError, 'image bytes'):
                publish(manifest)


if __name__ == '__main__':
    unittest.main()
