"""Adversarial cases at the fixed-base and logical-net boundaries."""
import json
import hashlib
import subprocess
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from check import digest, verify
from handoff import verify_handoff
from repair import repair
from repeaters import check_allocations, inventory
from resource_search import route_resources
from search import route


def pin(x, y):
    return [[x-2, y-2, x+2, y+2]]


def make_spec(pins, nets):
    via = {'cut': 2, 'spacing': 3, 'lower_enclosure': 1, 'upper_enclosure': 1}
    return {'schema_version': 'upper-router/1', 'units': 'dbu',
            'technology': {'bounds': [0, 0, 220, 120], 'origin': [0, 0], 'pitch': 10,
                           'width': 2, 'spacing': 2, 'via10': via.copy(), 'via11': via.copy()},
            'pins': {name: pin(*position) for name, position in pins.items()},
            'nets': [{'id': name, 'driver': driver, 'sinks': sinks} for name, driver, sinks in nets]}


def relay(name, y, status='virtual'):
    return {'id': name, 'status': status, 'power': 'assumed' if status == 'virtual' else 'verified',
            'native_view_sha256': 'a'*64, 'footprint_dbu': [85, y-4, 115, y+4],
            'input': {'id': name+'/A', 'm10': pin(90, y)},
            'output': {'id': name+'/Y', 'm10': pin(110, y)},
            'input_cap_ff': 4, 'output_limit_ff': 95}


def relay_data(*resources):
    return {'schema_version': 'upper-repeaters/1', 'units': 'dbu', 'repeaters': list(resources),
            'electrical': {'wire_cap_ff_per_dbu': 1, 'driver_limits_ff': {'source': 90}}}


def default_net():
    return make_spec({'source': (20, 30), 'sink': (180, 30)}, [('a/path', 'source', ['sink'])])


class FixedBaseTests(unittest.TestCase):
    def test_fine_access_uses_only_local_windows(self):
        spec = make_spec({'one': (22, 22), 'two': (178, 22)}, [('unknown', 'one', ['two'])])
        self.assertEqual(route(spec)['failed'], {'unknown': 'grid_access_not_found'})
        spec['technology'].update(access_pitch=2, access_radius=16)
        result = route(spec)
        self.assertEqual(result['failed'], {})
        self.assertEqual([p['at'] for p in result['routes']['unknown']['via10']], [[22, 22], [178, 22]])
        self.assertEqual(result['geometry_check']['via10_count'], 2)
        route_rows = result['routes']['unknown']['segments']
        route_rows.append({'layer': 'M11', 'a': [60, 22], 'b': [70, 22]})
        with self.assertRaisesRegex(ValueError, 'declared coarse or local'):
            verify(spec, result)

    def test_same_net_cuts_still_have_spacing_on_fine_grid(self):
        spec = make_spec({'one': (20, 20), 'two': (24, 20)}, [('close', 'one', ['two'])])
        spec['technology']['access_pitch'] = 2
        result = route(spec)
        self.assertIn('close', result['failed'])

    def test_foreign_m10_conductor_blocks_route_and_forged_readback(self):
        spec = default_net()
        result = route(spec)
        spec['pins']['unrelated native terminal'] = [[21, 29, 23, 31]]
        result['spec_sha256'] = digest(spec)
        self.assertEqual(route(spec)['failed'], {'a/path': 'grid_access_not_found'})
        with self.assertRaisesRegex(ValueError, 'foreign M10 pin'):
            verify(spec, result)

    def test_conflict_round_preserves_unrelated_route(self):
        spec = json.loads((Path(__file__).parent/'examples'/'ripup.json').read_text())
        spec['pins'].update(c0=pin(8, 56), c1=pin(24, 56))
        spec['nets'].append({'id': 'unrelated', 'driver': 'c0', 'sinks': ['c1']})
        baseline = route(spec, rounds=1)
        self.assertEqual(baseline['attempts'][0]['blockers'], {'b': ['a']})
        result = route(spec, rounds=2)
        self.assertFalse(result['failed'])
        self.assertEqual(result['attempts'][1]['kept'], ['unrelated'])
        self.assertEqual(result['routes']['unrelated'], baseline['routes']['unrelated'])

    def test_repeaters_serve_overload_and_separate_physical_stages(self):
        spec = default_net()
        plain = route_resources(spec, relay_data())
        self.assertGreater(plain['estimated_stage_loads']['segment/0/0']['over_ff'], 0)
        data = relay_data(relay('any-name', 30))
        buffered = route_resources(spec, data)
        self.assertEqual(buffered['allocations']['a/path']['repeater'], 'any-name')
        self.assertEqual(buffered['used_virtual'], ['any-name'])
        self.assertFalse(buffered['physical_qualified'])
        self.assertEqual(set(buffered['physical_routes']['routes']), {'segment/0/0', 'segment/0/1'})
        self.assertTrue(all(v['over_ff'] == 0 for v in buffered['estimated_stage_loads'].values()))

    def test_two_stage_chain_and_duplicate_channel_attack(self):
        spec = default_net()
        spec['pins']['sink'] = pin(300, 30)
        spec['technology']['bounds'][2] = 330
        second = relay('far', 30)
        second.update(footprint_dbu=[185, 26, 215, 34],
                      input={'id': 'far/A', 'm10': pin(190, 30)},
                      output={'id': 'far/Y', 'm10': pin(210, 30)})
        data = relay_data(relay('near', 30), second)
        one = route_resources(spec, data, rounds=1)
        self.assertTrue(any(v['over_ff'] > 0 for v in one['estimated_stage_loads'].values()))
        two = route_resources(spec, data, rounds=1, max_repeaters=2)
        self.assertEqual(two['allocations']['a/path']['chain'], ['near', 'far'])
        self.assertTrue(all(v['over_ff'] == 0 for v in two['estimated_stage_loads'].values()))
        two['allocations']['a/path']['chain'] = ['near', 'near']
        with self.assertRaisesRegex(ValueError, 'shared repeater'):
            check_allocations(spec, data, two)

    def test_512_bit_bundle_with_unrelated_handshake_and_generic_names(self):
        pins = {p: (x, 20+i*10) for i in range(513)
                for p, x in [('A-%d' % i, 20), ('B-%d' % i, 40)]}
        nets = [('bit/%d' % i, 'A-%d' % i, ['B-%d' % i]) for i in range(512)]
        nets.append(('some-return', 'B-512', ['A-512']))
        spec = make_spec(pins, nets)
        spec['technology']['bounds'][3] = 5160
        spec['bundles'] = [{'id': 'opaque group', 'members': [n[0] for n in nets[:-1]]}]
        result = route(spec)
        self.assertFalse(result['failed'])
        self.assertEqual(result['geometry_check']['nets_checked'], 513)
        self.assertEqual(result['geometry_check']['via10_count'], 1026)
        self.assertEqual(result['attempts'][0]['order'][-1], 'some-return')
        spec['bundles'].append({'id': 'bad membership', 'members': ['bit/1']})
        with self.assertRaisesRegex(ValueError, 'invalid routing bundle'):
            route(spec)

    def test_branch_repeater_leaves_near_load_direct(self):
        spec = default_net()
        spec['pins']['local'] = pin(40, 30)
        spec['nets'][0]['sinks'].append('local')
        data = relay_data(relay('split', 30))
        data['electrical']['sink_caps_ff'] = {'local': 12}
        result = route_resources(spec, data)
        self.assertEqual(result['allocations']['a/path']['sinks'], ['sink'])
        self.assertEqual(result['physical_spec']['nets'][0]['sinks'], ['local', 'split/A'])

    def test_contention_does_not_share_an_instance(self):
        spec = default_net()
        spec['pins'].update(other=pin(20, 40), target=pin(180, 40))
        spec['nets'].append({'id': 'another', 'driver': 'other', 'sinks': ['target']})
        data = relay_data(relay('only-one', 30))
        data['electrical']['driver_limits_ff'].update(other=90)
        result = route_resources(spec, data, rounds=3)
        used = [x['repeater'] for x in result['allocations'].values() if x]
        self.assertEqual(used, ['only-one'])
        self.assertEqual(len(result['attempts']), 3)
        forgery = deepcopy(result)
        for name, allocation in forgery['allocations'].items():
            if allocation is None:
                forgery['allocations'][name] = {'repeater': 'only-one', 'sinks': ['target' if name == 'another' else 'sink']}
        with self.assertRaisesRegex(ValueError, 'shared repeater'):
            check_allocations(spec, data, forgery)

    def test_check_reconstructs_split_even_if_forgery_is_resealed(self):
        spec, data = default_net(), relay_data(relay('R', 30))
        result = route_resources(spec, data)
        result['physical_spec']['nets'][1]['sinks'] = ['source']
        result['physical_routes']['spec_sha256'] = digest(result['physical_spec'])
        with self.assertRaisesRegex(ValueError, 'logical projection'):
            check_allocations(spec, data, result)

    def test_physical_inventory_and_keepouts_fail_closed(self):
        spec = default_net()
        data = relay_data(relay('R', 30))
        data['native_keepouts'] = [[100, 25, 115, 32]]
        with self.assertRaisesRegex(ValueError, 'footprint overlap'):
            inventory(spec, data)
        data = relay_data(relay('R', 30, 'physical'))
        data['repeaters'][0]['native_view_sha256'] = 'bad'
        with self.assertRaisesRegex(ValueError, 'native view identity'):
            inventory(spec, data)

    def test_virtual_cannot_emit_physical_def(self):
        spec, data = default_net(), relay_data(relay('R', 30))
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder/'in.json').write_text(json.dumps(spec))
            (folder/'relay.json').write_text(json.dumps(data))
            process = subprocess.run([sys.executable, '-B', str(Path(__file__).with_name('run.py')),
                                      str(folder/'in.json'), str(folder/'out.json'),
                                      '--repeaters', str(folder/'relay.json'), '--emit-def', str(folder/'def'),
                                      '--dbu-per-micron', '1000', '--via-resistance-ohm', '0.08'],
                                     capture_output=True, text=True)
            self.assertNotEqual(process.returncode, 0)
            self.assertIn('virtual repeaters cannot enter physical DEF', process.stderr)
            self.assertFalse((folder/'def').exists())

    def test_measured_repair_freezes_unaffected_geometry_and_checks_hash(self):
        spec = default_net()
        spec['pins'].update(fixed0=pin(20, 90), fixed1=pin(80, 90))
        spec['nets'].append({'id': 'z/fixed', 'driver': 'fixed0', 'sinks': ['fixed1']})
        data = relay_data(relay('optional', 30, 'physical'))
        data['electrical']['driver_limits_ff'].clear()
        previous = route_resources(spec, data)
        self.assertIsNone(previous['allocations']['a/path'])
        feedback = {'schema_version': 'upper-route-feedback/1', 'evidence': 'fixture-sta.rpt',
                    'route_sha256': digest(previous['physical_routes']),
                    'violations': [{'segment': 'segment/0/0', 'metric': 'setup', 'measured': -1, 'limit': 0}]}
        result = repair(spec, data, previous, feedback)
        self.assertEqual(result['repair']['status'], 'requires_new_extraction')
        self.assertEqual(result['physical_routes']['routes']['segment/1/0'],
                         previous['physical_routes']['routes']['segment/1/0'])
        feedback['route_sha256'] = 'stale'
        with self.assertRaisesRegex(ValueError, 'stale measured'):
            repair(spec, data, previous, feedback)

    def test_resealed_handoff_still_rejects_missing_required_signal(self):
        spec = default_net()
        spec['context'] = {'base_id': 'literal base', 'base_sha256': 'frozen'}
        program = {'source': {'plan': 'any upstream'}}
        members = [{'id': 'wire/bit/0', 'driver': 'source', 'sinks': ['sink']}]
        wiring = {'source': program['source'], 'members': members, 'users': {}, 'unresolved': []}
        request = {'source': program['source'], 'base_id': 'literal base', 'base_sha256': 'frozen',
                   'status': 'endpoint_binding_complete', 'unresolved': [],
                   'members': members, 'users': {},
                   'nets': [dict(n, members=['wire/bit/0'], fixed_sinks=[]) for n in spec['nets']]}
        request['sha256'] = digest(request)
        spec['context']['request_sha256'] = request['sha256']
        receipt = {'route_scope': 'product', 'status': 'ready_for_algorithm_2', 'unresolved': [],
                   'router_input_sha256': digest(spec), 'program_sha256': digest(program),
                   'wiring_sha256': digest(wiring), 'source': program['source'], 'base_sha256': 'frozen',
                   'request_sha256': request['sha256'], 'coverage': {'new_signal_nets': 1}}
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            for name, value in (('program', program), ('wiring', wiring),
                                ('requirements', request), ('handoff', receipt)):
                (folder/(name+'.json')).write_text(json.dumps(value))
            self.assertEqual(verify_handoff(spec, folder)['scope'], 'product')
            spec['nets'] = []
            receipt['router_input_sha256'] = digest(spec)
            (folder/'handoff.json').write_text(json.dumps(receipt))
            with self.assertRaisesRegex(ValueError, 'bound static netlist'):
                verify_handoff(spec, folder)

    def test_product_rebind_rejects_resealed_fake_fixed_sink(self):
        from adapter import bind_request
        from route_contract import bind_members, seal

        old = default_net()
        members = [{'id': 'wire/0', 'driver': 'source', 'sinks': ['sink']}]
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            payload = b'test native view'
            (folder/'view').write_bytes(payload)
            views = {key: {'path': 'view', 'sha256': hashlib.sha256(payload).hexdigest()}
                     for key in ('odb', 'gds', 'netlist')}
            base = {'schema_version': 'route-contract/1', 'base_id': 'any', 'state': 'frozen',
                    'dbu_per_micron': 2000, 'views': views,
                    'endpoints': {p: {'odb_term': p, 'native_net': p, 'role': role,
                                      'm10_shapes': [{'layer': 'M10', 'object': p,
                                                      'rect_dbu': old['pins'][p][0]}]}
                                  for p, role in [('source', 'driver'), ('sink', 'sink')]}}
            nets, missing = bind_members(members, base)
            self.assertFalse(missing)
            program = {'source': {'plan': 'one'}}
            wiring = {'source': program['source'], 'members': members, 'users': {}, 'unresolved': []}
            request = {'source': program['source'], 'base_id': base['base_id'], 'base_sha256': digest(base),
                       'status': 'endpoint_binding_complete', 'unresolved': [], 'members': members,
                       'users': {}, 'nets': nets}
            for name, value in (('base', base), ('program', program), ('wiring', wiring)):
                (folder/(name+'.json')).write_text(json.dumps(value))
            for fixed in (False, True):
                if fixed:
                    request['nets'][0]['fixed_sinks'] = ['sink']
                bound = seal(request)
                spec = bind_request(bound, base, old['technology'])
                receipt = {'route_scope': 'product', 'status': 'ready_for_algorithm_2', 'unresolved': [],
                           'router_input_sha256': digest(spec), 'program_sha256': digest(program),
                           'wiring_sha256': digest(wiring), 'source': program['source'],
                           'base_sha256': digest(base), 'request_sha256': bound['sha256'],
                           'coverage': {'new_signal_nets': int(not fixed)}}
                (folder/'requirements.json').write_text(json.dumps(bound))
                (folder/'handoff.json').write_text(json.dumps(receipt))
                if fixed:
                    with self.assertRaisesRegex(ValueError, 'fixed sinks differ'):
                        verify_handoff(spec, folder, folder/'base.json')
                else:
                    result = verify_handoff(spec, folder, folder/'base.json')
                    self.assertEqual(result['native_gds_sha256'], views['gds']['sha256'])
