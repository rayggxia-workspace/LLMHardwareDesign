import csv
import json
from pathlib import Path
import tempfile
import unittest

from adapter import bind_request
from geometry import validate
from native_inventory import INPUTS, VIEWS, build, file_hash
from route_contract import VERSION, read_base


def save_json(path, value):
    path.write_text(json.dumps(value), encoding='utf-8')


def save_table(path, records):
    with path.open('w', encoding='utf-8', newline='') as stream:
        output = csv.DictWriter(stream, records[0], delimiter='\t', lineterminator='\n')
        output.writeheader()
        output.writerows(records)


class NativeInventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)
        fixture = self.path / 'fixture'
        fixture.mkdir()
        refs = {}
        for name in VIEWS.values():
            artifact = fixture / name
            artifact.write_bytes(name.encode())
            refs[name] = {'path': str(artifact), 'sha256': file_hash(artifact)}
        self.index = {'schema': 'issue185-native-leaf-endpoint-evidence/1', 'role_counts': {
            'ROLE': {'design': {'design': 'anonymous', 'dbu_per_um': '2000', 'x0': '0',
                                'y0': '0', 'x1': '160', 'y1': '160'},
                     'exact_fixture_sources': refs}}}
        self.endpoint_rows = []
        self.cuts = []
        self.legs = []
        for i in range(2):
            cut = f'path/{i}'
            cut_pins = []
            for port, direction, x in [(f'output[{i}]', 'OUTPUT', 20),
                                       (f'input[{i}]', 'INPUT', 80)]:
                net = f'physical/{port}'
                coords = [[x, i * 20 + 10, x + 10, i * 20 + 20]]
                cut_pins.append({'name': port, 'net': net, 'direction': direction, 'bbox_dbu': coords})
                self.endpoint_rows.append({
                    'role': 'role', 'kind': 'fixture_bterm', 'term': port, 'net': net,
                    'pin_key': f'BTERM/{port}', 'direction': direction, 'formal_cut_candidate': cut,
                    'endpoint_scope': 'split_fixture_m10_bterm', 'm10_pin_boxes_dbu': json.dumps(coords),
                    'raw_full_parent_m10_mask': 'True', 'same_net_positive_area_layers': 'metal10',
                    'spef_net': net, 'spef_terminal_component': f'spef/{port}',
                })
                self.legs.append({
                    'role': 'role', 'candidate': cut, 'side': 'fixture_split_side', 'lower_net': net,
                    'bterms': json.dumps([port]), 'all_pad_to_directional_spef': 'True',
                    'physical_drivers': '["driver/Z"]' if direction == 'OUTPUT' else '[]',
                    'physical_receivers': '["sink/A"]' if direction == 'INPUT' else '[]',
                })
            self.cuts.append({
                'role': 'role', 'candidate': cut, 'fixture_m10_bterms': json.dumps(cut_pins),
                'fixture_lower_nets': json.dumps([pin['net'] for pin in cut_pins]),
                'has_single_logical_driver': 'True', 'requires_routing': 'True',
                'original_lower_driver_iterms': '[]', 'original_lower_receiver_iterms': '[]',
            })
        self.catalog = {'schema_version': VERSION, 'demands': {'bus': {
            'signals': [{'name': 'bit', 'width': 2, 'driver': 'output[{bit}]',
                         'sinks': ['input[{bit}]']}], 'requires': []}}}
        self.users = {'bus': []}

    def seal(self):
        save_json(self.path / 'inventory.json', self.index)
        save_table(self.path / 'endpoint-inventory.tsv', self.endpoint_rows)
        save_table(self.path / 'candidate-cut-legs.tsv', self.legs)
        save_table(self.path / 'logical-cut-candidates.tsv', self.cuts)
        self.manifest = self.path / 'inventory-files.sha256'
        self.manifest.write_text(''.join(f'{file_hash(self.path / name)}  {name}\n' for name in INPUTS),
                                 encoding='ascii')
        return file_hash(self.manifest)

    def build(self):
        return build(self.path, self.seal(), 'role', self.catalog, self.users)

    def test_existing_schemas_bind_all_bits_and_carry_fixture_scope(self):
        base, request = self.build()
        self.assertEqual(base['state'], 'candidate')
        self.assertEqual(request['status'], 'endpoint_binding_complete')
        self.assertFalse(request['physical_qualified'])
        self.assertEqual(len(request['members']), 2)
        self.assertEqual(request['source']['selected_fixture_cuts'], {'path/0':'bus/bit/0', 'path/1':'bus/bit/1'})
        save_json(self.path / 'base.json', base)
        tech = {'bounds': base['bounds_dbu'], 'origin': [0, 0], 'pitch': 10, 'width': 2,
                'spacing': 2, 'via10': {'cut': 2, 'lower_enclosure': 1, 'upper_enclosure': 1, 'spacing': 2},
                'via11': {'cut': 2, 'lower_enclosure': 1, 'upper_enclosure': 1, 'spacing': 2}}
        spec = bind_request(request, read_base(self.path / 'base.json'), tech)
        validate(spec)
        self.assertEqual(spec['context']['native_inventory']['scope'], 'native_cut_fixture')
        self.assertEqual(len(spec['nets']), 2)

    def test_reject_wrong_manifest_and_edited_table(self):
        digest = self.seal()
        with self.assertRaisesRegex(ValueError, 'manifest fingerprint differs'):
            build(self.path, '0' * 64, 'role', self.catalog, self.users)
        with (self.path / 'candidate-cut-legs.tsv').open('a', encoding='utf-8') as file:
            file.write('\n')
        with self.assertRaisesRegex(ValueError, 'member fingerprint differs'):
            build(self.path, digest, 'role', self.catalog, self.users)

    def test_reject_source_view_with_wrong_bytes(self):
        (self.path / 'fixture/gds').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError, 'native view fingerprint differs: gds'):
            self.build()

    def test_reject_swapped_vector_bits_on_distinct_native_cut_owners(self):
        signals = self.catalog['demands']['bus']['signals']
        signals[0]['width'] = 1
        signals[0]['sinks'] = ['input[1]']
        with self.assertRaisesRegex(ValueError, 'cross authoritative logical cut'):
            self.build()

    def test_reject_half_cut_and_unexpanded_dependency(self):
        self.endpoint_rows.pop(1)
        with self.assertRaisesRegex(ValueError, 'missing source-bound endpoint'):
            self.build()
        self.catalog['demands']['bus']['requires'].append('omitted')
        with self.assertRaisesRegex(ValueError, 'unexpanded source demand'):
            self.build()

    def test_reject_landed_geometry_without_rc_owner(self):
        self.endpoint_rows[1]['spef_terminal_component'] = ''
        with self.assertRaisesRegex(ValueError, 'ownership or resistor witness'):
            self.build()

    def test_reject_resistor_leg_and_native_iterm_without_access(self):
        self.legs[1]['all_pad_to_directional_spef'] = 'False'
        with self.assertRaisesRegex(ValueError, 'cut leg lacks'):
            self.build()
        self.cuts[0]['original_lower_receiver_iterms'] = '["leaf/A"]'
        with self.assertRaisesRegex(ValueError, 'ITerm sides without'):
            self.build()

    def test_reject_competing_drivers_on_one_native_component(self):
        first, second = self.endpoint_rows[1], self.endpoint_rows[3]
        second['net'] = first['net']
        second['spef_terminal_component'] = first['spef_terminal_component']
        self.legs[3]['lower_net'] = first['net']
        witnesses = json.loads(self.cuts[1]['fixture_m10_bterms'])
        witnesses[1]['net'] = first['net']
        self.cuts[1]['fixture_m10_bterms'] = json.dumps(witnesses)
        self.cuts[1]['fixture_lower_nets'] = json.dumps([pin['net'] for pin in witnesses])
        with self.assertRaisesRegex(ValueError, 'competing ownership'):
            self.build()


if __name__ == '__main__':
    unittest.main()
