"""Bind a source-verified native fixture inventory to route-contract/1."""
import argparse
import csv
from hashlib import sha256
import json
from pathlib import Path
import re

# The adapter already loads the matching route_contract implementation.
from adapter import bind_request
from geometry import validate
from route_contract import VERSION, elaborate, expand, require, verify_requirements


HASH = re.compile(r'[0-9a-f]{64}\Z')
VIEWS = {'odb': 'odb', 'def': 'def', 'gds': 'gds', 'netlist': 'v', 'spef': 'spef'}
INPUTS = ('inventory.json', 'endpoint-inventory.tsv', 'candidate-cut-legs.tsv',
          'logical-cut-candidates.tsv')
INVENTORY_VERSION = 'issue185-native-leaf-endpoint-evidence/1'


def file_hash(path):
    digest = sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def records(path, role):
    with path.open(encoding='utf-8', newline='') as source:
        return [row for row in csv.DictReader(source, delimiter='\t') if row['role'] == role]


def unique(rows, key, description):
    result = {}
    for row in rows:
        name = row[key]
        require(name and name not in result, f'duplicate or blank {description}: {name}')
        result[name] = row
    return result


def open_inventory(directory, expected_manifest_sha256):
    manifest = directory / 'inventory-files.sha256'
    require(HASH.fullmatch(expected_manifest_sha256) and file_hash(manifest) == expected_manifest_sha256,
            'inventory manifest fingerprint differs')
    entries = {}
    for line in manifest.read_text(encoding='utf-8').splitlines():
        digest, name = line.split(maxsplit=1)
        require(HASH.fullmatch(digest) and name not in entries, 'invalid inventory manifest entry')
        entries[name] = digest
    for name in INPUTS:
        require(entries.get(name) == file_hash(directory / name), f'inventory member fingerprint differs: {name}')
    index = read_json(directory / 'inventory.json')
    require(index.get('schema') == INVENTORY_VERSION, 'unsupported native inventory schema')
    return index, {name: entries[name] for name in INPUTS}


def physical_views(source, view_paths):
    result = {}
    require(set(view_paths) <= VIEWS.keys(), 'unknown native view override')
    for view, suffix in VIEWS.items():
        receipt = source[suffix]
        path = Path(view_paths.get(view, receipt['path'])).resolve()
        require(path.is_file() and file_hash(path) == receipt['sha256'], f'native view fingerprint differs: {view}')
        result[view] = {'path': str(path), 'sha256': receipt['sha256']}
    return result


def contains(outer, inner):
    return outer[0] <= inner[0] < inner[2] <= outer[2] and outer[1] <= inner[1] < inner[3] <= outer[3]


def physical_endpoint(row, role, bounds):
    port = row['term']
    require(row['endpoint_scope'] == 'split_fixture_m10_bterm', f'not a qualified cut BTerm: {port}')
    require(row['raw_full_parent_m10_mask'] == 'True'
            and 'metal10' in row['same_net_positive_area_layers'].split(';')
            and row['spef_net'] and row['spef_terminal_component'] and row['net'],
            f'missing native M10 ownership or resistor witness: {port}')
    expected_direction = 'OUTPUT' if role == 'driver' else 'INPUT'
    require(row['direction'] == expected_direction, f'physical endpoint direction mismatch: {port}')
    rectangles = json.loads(row['m10_pin_boxes_dbu'])
    require(rectangles and all(isinstance(box, list) and len(box) == 4
                               and all(type(x) is int for x in box) and contains(bounds, box)
                               for box in rectangles)
            and len({tuple(box) for box in rectangles}) == len(rectangles),
            f'invalid native M10 rectangle: {port}')
    return {
        'odb_term': port, 'native_net': row['net'], 'role': role,
        'm10_shapes': [{'layer': 'M10', 'object': f'BTERM/{port}/M10/{i}', 'rect_dbu': box}
                       for i, box in enumerate(rectangles)],
        'source_pin_key': row['pin_key'], 'source_resistor_component': row['spef_terminal_component'],
    }


def select_cut_members(members, endpoint_rows, leg_rows, cuts, bounds):
    # Fixture cuts are chosen explicitly through the regular #227 catalog.
    endpoints = {}
    components = {}
    chosen = {}
    for member in members:
        driver, sinks = member['driver'], member['sinks']
        terminals = [driver] + sinks
        for port in terminals:
            require(port in endpoint_rows, f'missing source-bound endpoint: {port}')
        cut = endpoint_rows[driver]['formal_cut_candidate']
        require(cut in cuts and all(endpoint_rows[p]['formal_cut_candidate'] == cut for p in terminals),
                f'endpoints cross authoritative logical cut ownership: {member["id"]}')
        record = cuts[cut]
        require(record['has_single_logical_driver'] == 'True' and record['requires_routing'] == 'True',
                f'invalid source cut direction or state: {cut}')
        require(not json.loads(record['original_lower_driver_iterms'])
                and not json.loads(record['original_lower_receiver_iterms']),
                f'cut has native ITerm sides without an authoritative exported BTerm: {cut}')
        pins = unique(json.loads(record['fixture_m10_bterms']), 'name', 'cut terminal')
        require(set(pins) == set(terminals), f'incomplete or extra physical sides of cut: {cut}')
        require({pin['net'] for pin in pins.values()} == set(json.loads(record['fixture_lower_nets']))
                and all(pins[s]['net'] != pins[driver]['net'] for s in sinks),
                f'cut is not divided across authoritative native nets: {cut}')
        require(cut not in chosen, f'cut has multiple requirements members: {cut}')
        chosen[cut] = member['id']
        for port, direction in zip(terminals, ['driver'] + ['sink'] * len(sinks)):
            row, pin = endpoint_rows[port], pins[port]
            require(pin['direction'] == row['direction'] and pin['net'] == row['net']
                    and pin['bbox_dbu'] == json.loads(row['m10_pin_boxes_dbu']),
                    f'logical and physical cut witnesses differ: {port}')
            leg = leg_rows.get((cut, port))
            require(leg and leg['side'] == 'fixture_split_side' and leg['lower_net'] == row['net']
                    and leg['all_pad_to_directional_spef'] == 'True',
                    f'cut leg lacks authoritative resistor witness: {port}')
            key = 'physical_drivers' if direction == 'driver' else 'physical_receivers'
            opposite = 'physical_receivers' if direction == 'driver' else 'physical_drivers'
            iterms = json.loads(leg[key])
            require(iterms and (direction != 'driver' or len(iterms) == 1)
                    and not json.loads(leg[opposite]),
                    f'cut leg has missing or competing functional terminal ownership: {port}')
            endpoint = physical_endpoint(row, direction, bounds)
            previous = components.setdefault(endpoint['native_net'], (row['spef_terminal_component'], driver))
            require(previous == (row['spef_terminal_component'], driver),
                    f'disconnected or competing ownership on native component: {endpoint["native_net"]}')
            require(port not in endpoints, f'physical BTerm reused by multiple members: {port}')
            endpoints[port] = {**endpoint, 'source_directional_iterms': iterms}
    return endpoints, chosen


def build(directory, manifest_sha256, role, catalog, users, view_paths=None):
    index, evidence = open_inventory(directory, manifest_sha256)
    role = role.lower()
    require(role.upper() in index['role_counts'], 'fixture role absent from source inventory')
    fixture = index['role_counts'][role.upper()]
    source = fixture['exact_fixture_sources']
    views = physical_views(source, view_paths or {})
    placement = fixture['design']
    units = int(placement['dbu_per_um'])
    bounds = [int(placement[k]) for k in ('x0', 'y0', 'x1', 'y1')]
    terminal_rows = unique((r for r in records(directory / 'endpoint-inventory.tsv', role)
                            if r['kind'] == 'fixture_bterm'), 'term', 'ODB BTerm')
    cuts = unique(records(directory / 'logical-cut-candidates.tsv', role), 'candidate', 'logical cut')
    legs = {}
    for row in records(directory / 'candidate-cut-legs.tsv', role):
        for port in json.loads(row['bterms']):
            key = (row['candidate'], port)
            require(key not in legs, f'cut BTerm has multiple lower legs: {port}')
            legs[key] = row
    _, _, members, unresolved = expand(users, catalog)
    require(members and not unresolved, 'missing or unexpanded source demand')
    endpoints, selected = select_cut_members(members, terminal_rows, legs, cuts, bounds)
    scope = 'native_cut_fixture'
    provenance = {
        'scope': scope, 'fixture_role': role, 'fixture_design': placement['design'],
        'inventory_manifest_sha256': manifest_sha256, 'inventory_members_sha256': evidence,
        'source_native_odb_sha256': views['odb']['sha256'], 'selected_fixture_cuts': selected,
    }
    base = {
        'schema_version': VERSION, 'state': 'candidate',
        'base_id': f'{scope}:{placement["design"]}:{views["odb"]["sha256"][:16]}',
        'dbu_per_micron': units, 'bounds_dbu': bounds, 'views': views,
        'endpoints': endpoints, 'fixed_native_nets': {}, 'native_inventory': provenance,
    }
    request = elaborate(users, catalog, base, provenance)
    verified = verify_requirements(request, users, catalog, base, provenance)
    require(verified['passed'] and not request['unresolved'], 'fixture request does not bind completely')
    return base, request


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('inventory', type=Path)
    parser.add_argument('catalog', type=Path, help='existing route-contract/1 interface catalog')
    parser.add_argument('users', type=Path, help='existing route-contract demand users mapping')
    parser.add_argument('output', type=Path, help='fixture output directory')
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--role', required=True)
    parser.add_argument('--view', action='append', default=[], metavar='KIND=PATH',
                        help='locally mounted copy of a source artifact with identical SHA-256')
    parser.add_argument('--rules', type=Path,
                        help='optionally bind existing #259 geometry input without running route search')
    args = parser.parse_args()
    try:
        overrides = dict(v.split('=', 1) for v in args.view)
        require(len(overrides) == len(args.view), 'duplicate native view override')
        base, request = build(args.inventory, args.manifest_sha256, args.role,
                              read_json(args.catalog), read_json(args.users), overrides)
        outputs = {'base': base, 'requirements': request}
        if args.rules:
            rules = read_json(args.rules)
            spec = bind_request(request, base, rules['technology'], rules.get('obstacles', []))
            validate(spec)
            outputs['router-input'] = spec
        args.output.mkdir(parents=True, exist_ok=True)
        for name, value in outputs.items():
            (args.output / (name + '.json')).write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
    except (OSError, ValueError, KeyError) as error:
        parser.exit(2, f'{error}\n')


if __name__ == '__main__':
    main()
