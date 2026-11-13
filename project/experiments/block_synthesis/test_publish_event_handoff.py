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
from route_contract import elaborate, verify_requirements
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
    def test_placed_parent_cuts_require_terminal_evidence_and_candidate_scope(self):
        _, _, _, catalog, base, _ = fixture()
        base['assembly_state'] = 'placed_parent_cuts'
        del base['fixed_native_nets']
        base['views'] = {kind: {'path': kind, 'sha256': 'a' * 64}
                         for kind in ('odb', 'cut_identity', 'leaf_access', 'parent_access')}
        for endpoint in base['endpoints'].values():
            endpoint['anchor_class'] = 'parent_escape_required'
        self.assertFalse(elaborate({'P0-P1': []}, catalog, base, {})['physical_qualified'])
        for key, value, reason in (
                ('state', 'frozen', 'candidate base'),
                ('fixed_native_nets', {'claimed': {'driver': 'open-out'}}, 'native realizations'),
                ('views', {'odb': base['views']['odb']}, 'terminal evidence')):
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, reason):
                elaborate({'P0-P1': []}, catalog, {**base, key: value}, {})
        del base['endpoints']['open-in']['anchor_class']
        with self.assertRaisesRegex(ValueError, 'access class'):
            elaborate({'P0-P1': []}, catalog, base, {})

    def test_product_search_excludes_fast_provider_missing_from_physical_dispatch(self):
        from run import compile_event_ir

        arch = hardware()
        arch.update(topology_id=25, control_groups={'lane0': {'site': 'P0', 'block_id': 3,
                                                            'control_net': 'control'}})
        arch['nets']['control'] = {'cost': 1, 'signals': [
            {'name': 'command', 'width': 1, 'driver': 'mother/out', 'sinks': ['lane0/in']},
            {'name': 'done', 'width': 1, 'driver': 'lane0/out', 'sinks': ['mother/in']},
        ]}
        services = arch['event_model']['services']
        services['produce'].update(control_site='P0', native_providers={'lane0': 'fast'})
        services['block-source'].update(control_site='P0', native_providers={'lane0': 'enabled'})
        arch['native_provider_contracts'] = {
            name: {'calls': [
                {'schema': 3, 'abi': 7, 'opcode': opcode, 'completion': 'service_done'}]}
            for name, opcode in (('fast', 4), ('enabled', 2))
        }
        arch['event_model']['live_out'] = ['x']
        model = {'tasks': [task('root',
                               binding('fast', stage('produce', outputs={'source': 'x'})),
                               binding('enabled', stage('block-source', outputs={'source': 'x'})))]}
        base = {'schema_version': 'route-contract/1', 'state': 'frozen', 'base_id': 'base',
                'dbu_per_micron': 2000,
                'views': {name: {'path': name, 'sha256': 'a'*64} for name in ('odb', 'netlist', 'gds')},
                'assemblies': [{'id': 'lane0', 'views': {'netlist': 'netlist'}}],
                'endpoints': {
                    pin: {'odb_term': pin, 'assembly': pin.split('/')[0], 'role': role, 'native_net': pin,
                          'm10_shapes': [{'layer': 'M10', 'object': pin, 'rect_dbu': [0, 0, 2, 2]}]}
                    for pin, role in (('mother/out', 'driver'), ('lane0/in', 'sink'),
                                      ('lane0/out', 'driver'), ('mother/in', 'sink'))
                }}
        target = {'group': 'lane0', 'id': 3, 'netlist_view': 'netlist', 'netlist_sha256': 'a'*64,
                  'routes': [{'schema': 3, 'abi': 7, 'opcode': 2, 'completions': ['service_done']}]}
        base['native_service_routes'] = {'schema': 'native-rtl-target-routes/1',
                                         'topology_id': 25, 'targets': [target]}
        result = compile_event_ir(model, arch, route_base=base)
        self.assertEqual(result['plan']['tasks'][0]['binding'], 'enabled')
        self.assertEqual(result['outputs']['program']['locals']['lane0'][0]['service'], 'block-source')
        self.assertEqual(result['plan']['nets'], ['control'])
        target['routes'][0]['requires'] = ['dma']
        qualified = compile_event_ir(model, arch, route_base=base, route_scope='interface')
        self.assertEqual(qualified['status'], 'no_plan_in_bounded_search')
        self.assertIn("missing physical native dispatch demands ['dma']",
                      qualified['native_dispatch_issues']['services']['block-source'])
        arch['nets']['dma'] = {'cost': 1, 'signals': [
            {'name': 'data', 'width': 1, 'driver': 'memory/out', 'sinks': ['lane0/memory-in']},
        ]}
        for pin, role in (('memory/out', 'driver'), ('lane0/memory-in', 'sink')):
            base['endpoints'][pin] = {
                'odb_term': pin, 'role': role, 'native_net': pin,
                'm10_shapes': [{'layer': 'M10', 'object': pin, 'rect_dbu': [0, 0, 2, 2]}],
            }
        qualified = compile_event_ir(model, arch, route_base=base, route_scope='interface')
        self.assertEqual(qualified['plan']['nets'], ['dma'])
        self.assertEqual(qualified['outputs']['wiring']['users']['dma'][0]['event_id'], 0)
        self.assertEqual(compile_event_ir(model, arch, route_base=base)['plan']['nets'], ['control', 'dma'])
        target['routes'][0]['requires'] = ['dma', 'dma']
        with self.assertRaisesRegex(ValueError, 'invalid native dispatch route requirements'):
            compile_event_ir(model, arch, route_base=base)
        del target['routes'][0]['requires']
        self.assertEqual(compile_event_ir(model, arch, route_base=base, route_scope='interface')
                         ['plan']['tasks'][0]['binding'], 'enabled')
        denied = {'schema': 3, 'abi': 7, 'opcode': 2, 'reason': 'descriptor header mismatch'}
        target['rejected_routes'] = [denied]
        with self.assertRaisesRegex(ValueError, 'invalid or duplicate native dispatch route'):
            compile_event_ir(model, arch, route_base=base)
        routes = target['routes']
        target['routes'] = []
        rejected = compile_event_ir(model, arch, route_base=base, route_scope='interface')
        self.assertEqual(rejected['status'], 'no_plan_in_bounded_search')
        self.assertEqual(rejected['native_dispatch_issues']['services']['block-source'],
                         'lane0: rejected native signature (3, 7, 2): descriptor header mismatch')
        self.assertIn('no physical service route', rejected['native_dispatch_issues']['services']['produce'])
        del target['rejected_routes']
        target['routes'] = routes
        target['netlist_sha256'] = 'b'*64
        with self.assertRaisesRegex(ValueError, 'differs from the target assembly'):
            compile_event_ir(model, arch, route_base=base)
        target['netlist_sha256'] = 'a'*64
        target['routes'][0]['completions'] = ['issue_only']
        rejected = compile_event_ir(model, arch, route_base=base)
        self.assertEqual(rejected['status'], 'no_plan_in_bounded_search')
        issues = rejected['native_dispatch_issues']['services']
        self.assertIn('no physical service route for signatures [(3, 7, 4)]', issues['produce'])
        self.assertIn('no physical completion', issues['block-source'])
        del base['native_service_routes']
        self.assertEqual(compile_event_ir(model, arch, route_base=base)['status'], 'no_plan_in_bounded_search')

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
    def test_selected_plan_seals_transitive_wires_for_both_backends(self):
        from run import compile_event_ir

        model, arch, _, catalog, base, rules = fixture()
        for i, (name, source) in enumerate((('credit', 'P0-P1'), ('reset', 'credit'))):
            catalog['demands'][source]['requires'] = [name]
            arch['nets'][name] = {'cost': 2}
            catalog['demands'][name] = {'signals': [
                {'name': name, 'width': 1, 'driver': f'{name}-out', 'sinks': [f'{name}-in']}
            ]}
            for x, suffix, role in ((20, 'out', 'driver'), (180, 'in', 'sink')):
                pin = f'{name}-{suffix}'
                y = 75 + i * 20
                base['endpoints'][pin] = {'odb_term': pin, 'role': role, 'native_net': pin,
                                          'm10_shapes': [{'layer': 'M10', 'object': pin,
                                                          'rect_dbu': [x-2, y-2, x+2, y+2]}]}
        result = compile_event_ir(model, arch, route_base=base, route_catalog=catalog, route_scope='interface')
        self.assertEqual(result['plan']['nets'], ['P0-P1', 'credit', 'reset'])
        self.assertEqual(result['plan']['wire_cost'], 5)
        self.assertEqual(set(result['outputs']['wiring']['users']), {'P0-P1'})
        pack = build(model, result['resolved_hardware'], result['plan'], catalog, base, rules,
                     bind_request, source_outputs=result['outputs'])
        self.assertEqual(set(pack['wiring']['users']), {'P0-P1', 'credit', 'reset', 'resident-control'})
        native = pack['native-route-requirements']
        wiring = result['outputs']['wiring']
        self.assertEqual(pack['handoff']['source']['plan_sha256'], native['source']['plan_sha256'])
        self.assertEqual(native['source'], result['outputs']['program']['source'])
        self.assertEqual(native['sha256'], pack['handoff']['native_route_request_sha256'])
        self.assertEqual(native['members'], wiring['members'])
        self.assertEqual(native['dependencies'], wiring['dependencies'])
        self.assertEqual(set(native['users']), {'P0-P1', 'credit', 'reset'})
        for field in ('catalog_sha256', 'base_sha256'):
            self.assertEqual(native[field], pack['requirements'][field])
        verify_requirements(native, wiring['users'], catalog, base, wiring['source'])
        with self.assertRaisesRegex(ValueError, 'route request differs'):
            verify_requirements(pack['requirements'], wiring['users'], catalog, base, wiring['source'])
        broken = deepcopy(result['plan'])
        broken['nets'].remove('reset')
        with self.assertRaisesRegex(ValueError, 'event plan summary differs'):
            build(model, result['resolved_hardware'], broken, catalog, base, rules, bind_request)

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

    def test_algo2_feedback_recompiles_same_candidate_pool(self):
        from adapter import failure_feedback
        from retry_event_route import retry
        from run import compile_event_ir

        model, hardware, _, catalog, base, rules = fixture()
        previous = compile_event_ir(model, hardware, route_base=base, route_catalog=catalog,
                                    route_scope='interface', emit_outputs=True)
        self.assertIn('P0-P1', previous['plan']['nets'])
        pack = build(model, previous['resolved_hardware'], previous['plan'], catalog, base, rules,
                     bind_request, source_outputs=previous['outputs'])
        request, spec = pack['requirements'], pack['algorithm2-input']
        routes = route(spec, rounds=1, max_expansions=1)
        self.assertEqual(len(routes['failed']), 1)
        routes['feedback'] = failure_feedback(request, routes, 'route-test')
        trial = retry(previous, base, request, spec, routes)
        self.assertEqual(trial['status'], 'planned')
        self.assertEqual(trial['route_trial']['excluded_demands'], ['P0-P1'])
        self.assertNotIn('P0-P1', trial['plan']['nets'])
        self.assertIn('P0-P1', previous['plan']['nets'])
        self.assertEqual(trial['plan']['external_read_bytes'], 16)
        self.assertEqual(trial['plan']['external_write_bytes'], 16)
        rebuilt = build(model, trial['resolved_hardware'], trial['plan'], catalog, base, rules,
                        bind_request, source_outputs=trial['outputs'])
        self.assertEqual(rebuilt['handoff']['coverage']['new_signal_nets'], 0)
        self.assertNotEqual(pack['handoff']['source']['plan_sha256'],
                            rebuilt['handoff']['source']['plan_sha256'])
        with self.assertRaisesRegex(ValueError, 'different router input'):
            retry(previous, base, request, {**spec, 'obstacles': [{'different': True}]}, routes)
        with self.assertRaisesRegex(ValueError, 'different base'):
            retry(previous, {**base, 'base_id': 'another'}, request, spec, routes)

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
