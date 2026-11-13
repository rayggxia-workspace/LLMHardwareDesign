"""Project sealed native request control and P read/fence demand to joint ODB cuts.

The output uses the normal Algo2 interface. Parent pads are staged BTerms;
connecting them to their placed cell terminals is a separate lower-route gate.
This projection does not qualify the native providers or the DDR data plane.
"""
import argparse
from collections import Counter, defaultdict
import csv
from hashlib import sha256
import json
import re
from pathlib import Path

from route_contract import digest, elaborate, read_base, require, verify_requirements
from adapter import bind_request
from geometry import access_points, contains, validate
from handoff import verify_handoff


DMA_FAMILIES = {
    'p_dma_desc': 'descriptor',
    'p_dma_weight': 'weight',
    'p_dma_mc_fence': 'fence',
}
SCOPE_SIGNATURE = (0x2505001, 0x2504D02, 2)


def read(path):
    return json.loads(path.read_bytes())


def file_sha(path):
    with path.open('rb') as stream:
        return sha256_file(stream)


def sha256_file(stream):
    h = sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b''):
        h.update(block)
    return h.hexdigest()


def seal_entries(path):
    pairs = [line.split('  ', 1) for line in path.read_text(encoding='ascii').splitlines()]
    entries = {name: checksum for checksum, name in pairs}
    require(len(entries) == len(pairs), f'duplicate sealed file in {path}')
    return entries


def table(path, fields=None):
    with path.open(encoding='utf-8', newline='') as stream:
        yield from csv.DictReader(stream, fieldnames=fields, delimiter='\t')


def cut_rows(path):
    """Read the exact sealed terminal file consumed by the OpenDB cut tool."""
    with path.open(encoding='utf-8') as stream:
        for header in stream:
            cut, parent, number, prior, count = header.rstrip('\n').split('\t')
            key = cut, int(number)
            terms = [next(stream).rstrip('\n').split('\t') for _ in range(int(count))]
            require(terms and all(len(term) == 2 for term in terms),
                    f'invalid terminals for {key}')
            yield key, parent, prior, terms


def term_id(cut, leg, anchor):
    if anchor['anchor_class'] == 'parent_escape_required':
        return f'upper_access_{cut}_{leg}'
    return anchor['instance'] + '/' + anchor['pin']


def endpoint_inventory(joint):
    landings = {}
    for row in table(joint / 'landing-plan.tsv',
                     ('cut', 'leg', 'role', 'odb_net', 'x0', 'y0', 'x1', 'y1')):
        key = row['cut'], int(row['leg'])
        require(key not in landings, f'duplicate parent landing {key}')
        landings[key] = row
    leaves = defaultdict(list)
    for row in table(joint / 'placed-A-native-m10.tsv'):
        leaves[row['cut'], int(row['leg'])].append(row)
    require(not (set(landings) & set(leaves)), 'leaf and parent landing alias')

    expected_terms = {key: terms for key, _, _, terms in
                      cut_rows(joint / 'odb-transport-open-cuts.tsv')}
    anchors = {}
    for identity in table(joint / 'cut-placed-A-identity.tsv'):
        key = identity['cut'], int(identity['leg'])
        require(key not in anchors, f'duplicate physical cut leg {key}')
        anchor_class = identity['anchor_class']
        require(anchor_class in ('leaf_m10', 'parent_escape_required'),
                f'unknown physical cut leg class {key}')
        rows = leaves[key] if anchor_class == 'leaf_m10' else [landings[key]]
        require(rows and all(r['odb_net'] == identity['native_net']
                             and r['role'] == identity['role'] for r in rows),
                f'cut and M10 identity differ for {key}')
        for row in rows:
            if anchor_class == 'leaf_m10':
                require([[row['instance'], row['pin']]] == expected_terms[key],
                        f'leaf terminal differs for {key}')
        meta = {**rows[0], 'anchor_class': anchor_class}
        cut, leg = key
        term = term_id(cut, leg, meta)
        anchors[key] = {
            'odb_term': term, 'native_net': identity['native_net'], 'role': identity['role'],
            'anchor_class': anchor_class,
            'm10_shapes': [{'layer': 'M10', 'object': f'{term}:M10:{i}',
                            'rect_dbu': [int(r[k]) for k in ('x0', 'y0', 'x1', 'y1')]}
                           for i, r in enumerate(rows)],
        }
    require(set(anchors) == set(landings) | set(leaves), 'M10 access tables contain unknown legs')
    require(len({row['native_net'] for row in anchors.values()}) == len(anchors),
            'distinct physical cut legs share a native net')
    return anchors


def control_edges(requirements, contract):
    index = {}
    for edge in contract['edges']:
        key = tuple((edge[side].lower(), edge[side + '_pin']) for side in ('source', 'sink'))
        require(key not in index, f'ambiguous parent logical edge {key}')
        index[key] = edge
    for member in requirements['members']:
        driver = member['driver'].split('/', 1)
        for sink in member['sinks']:
            owner, pin = sink.split('/', 1)
            key = ((driver[0].lower(), driver[1]), (owner.lower(), pin))
            require(key in index and index[key]['kind'] not in DMA_FAMILIES,
                    f'control member absent in parent contract: {key}')
            yield member['demand_id'], index[key]


def dma_edges(contract, users):
    for edge in contract['edges']:
        family = DMA_FAMILIES.get(edge['kind'])
        if family is None:
            continue
        group = edge['sink'] if edge['source'] == 'dma' else edge['source']
        demand = f'dma:{group}:{family}'
        if demand in users:
            yield demand, edge


def edge_names(edge):
    source = edge['source']
    sink = edge['sink']
    a = source + '__' + edge.get('physical_source_net', edge['source_pin'])
    b = sink + '__' + edge.get('physical_sink_net', edge['sink_pin'])
    return a, b


def select_endpoints(selected, catalog, aliases, cuts, anchors):
    drivers = {}
    sinks = {}
    for key, parent, prior, _ in cuts:
        require(key in anchors and anchors[key]['role'] == ('driver' if key[1] == 0 else 'sink'),
                f'cut role differs for {key}')
        if key[1] == 0:
            require(parent == prior and parent not in drivers, f'ambiguous driver cut {parent}')
            drivers[parent] = key
        else:
            require((parent, prior) not in sinks, f'ambiguous sink leg {prior}')
            sinks[parent, prior] = key
    require(len(drivers) + len(sinks) == len(anchors), 'incomplete cut inventory')

    endpoints = {}
    coverage = Counter()
    for demand, edge in selected:
        source, sink = edge_names(edge)
        parent = aliases[source]
        source_anchor = anchors[drivers[parent]]
        sink_anchor = anchors[sinks[parent, sink]]
        require(source_anchor['native_net'] == parent,
                f'physical source ownership differs for {source}')
        for side, anchor in (('source', source_anchor), ('sink', sink_anchor)):
            name = edge[side] + '/' + edge[side + '_pin']
            require(endpoints.setdefault(name, anchor) == anchor,
                    f'inconsistent logical terminal alias {name}')
        a = edge['source'] + '/' + edge['source_pin']
        b = edge['sink'] + '/' + edge['sink_pin']
        catalog[demand]['signals'].append({'name': a + '->' + b, 'width': 1,
                                           'driver': a, 'sinks': [b]})
        coverage[demand] += 1
    return endpoints, coverage


def source_aliases(path, physical, selected):
    """Recover logical BTerm aliases from the exact pre-join DEF."""
    unknown = {edge_names(edge)[0] for _, edge in selected} - physical.keys()
    alias_to_prior = {}
    port = re.compile(r'^\s*-\s+(\S+)\s+\+ NET\s+(\S+)\s+\+ DIRECTION OUTPUT\b')
    with path.open(encoding='utf-8') as stream:
        for line in stream:
            if line.startswith('PINS '):
                break
        for line in stream:
            if line.startswith('END PINS'):
                break
            match = port.match(line)
            if match and match[1] in unknown:
                require(match[1] not in alias_to_prior, 'duplicate pre-join BTerm')
                alias_to_prior[match[1]] = match[2]
    require(alias_to_prior.keys() == unknown, 'source aliases missing from sealed pre-join DEF')
    require(all(prior in physical for prior in alias_to_prior.values()),
            'source alias without joined physical driver')
    return {**physical, **{name: physical[prior] for name, prior in alias_to_prior.items()}}, alias_to_prior


def check_constant_ties(joint, contract, active_groups):
    binding = read(joint / 'control-binding.json')
    audit = read(joint / 'odb-packet-dma-binding-audit.json')
    constants = contract['constants']
    require(audit['constant_sink_bits'] == len(constants)
            and len(binding['constant_tie_sinks']) == len(constants),
            'constant-tie audit coverage differs')
    selected = []
    for row in constants:
        group, _ = row['source_provenance']
        sink = row['sink'] + '__' + row['sink_pin']
        require(binding['constant_tie_sinks'].get(sink) == row['constant'],
                f'inconsistent constant tie {sink}')
        if group in active_groups:
            selected.append(row)
    return selected


def inventory_views(joint, prejoin):
    rows = {
        'odb': ('cut-placed-A-landings.odb', 'put-m10-landings.sha256'),
        'cut_identity': ('cut-placed-A-identity.tsv', 'cut-placed-A.sha256'),
        'cut_source': ('odb-transport-open-cuts.tsv', 'cut-placed-A.sha256'),
        'leaf_access': ('placed-A-native-m10.tsv', 'put-m10-landings.sha256'),
        'parent_access': ('landing-plan.tsv', 'landing-plan.sha256'),
        'placement_bounds': ('landing-obstacles.tsv', 'landing-plan.sha256'),
    }
    views = {name: {'path': str(joint / artifact),
                    'sha256': seal_entries(joint / manifest)[artifact]}
             for name, (artifact, manifest) in rows.items()}
    views['prejoin_def'] = {'path': str(prejoin),
                            'sha256': seal_entries(prejoin.with_suffix('.sha256'))[prejoin.name]}
    for name in views.keys() - {'odb', 'prejoin_def'}:
        require(file_sha(Path(views[name]['path'])) == views[name]['sha256'],
                f'sealed artifact changed: {name}')
    return views


def plan_users(control, signatures):
    users = dict(control['users'])
    active_groups = set()
    for demand, services in control['users'].items():
        for service in services:
            key = tuple(service[k] for k in ('schema', 'abi', 'opcode'))
            if key != SCOPE_SIGNATURE:
                continue
            require(service['site'].startswith('P') and demand == 'packet:' + service['site'],
                    'scope service is not bound to its packet target')
            identity = tuple(service[k] for k in ('target', 'schema', 'abi', 'opcode', 'completion'))
            require(identity in signatures, 'scope use absent from sealed native signatures')
            group = service['site']
            active_groups.add(group)
            for family in DMA_FAMILIES.values():
                users.setdefault(f'dma:{group}:{family}', []).append(service)
    require(active_groups, 'no P scopes in the supplied native request')
    return users, active_groups


def write(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def project(joint, prejoin, native, control_dir, out):
    require(out.is_dir() and not (out / 'base.json').exists(), 'use a fresh output folder')
    control = read(control_dir / 'requirements.json')
    prior = read(control_dir / 'algorithm2-input.json')
    report = read(control_dir / 'report.json')
    proof = seal_entries(native / 'proof.sha256')
    source = control['source']
    for role, name in (('service_signatures_sha256', 'service-signatures.json'),
                       ('mother_targets_sha256', 'mother-targets.tsv')):
        require(source[role] == proof[name] == file_sha(native / name),
                f'prior control output refers to a different {name}')
    require(source['package_proof_sha256'] == file_sha(native / 'proof.sha256')
            and control['sha256'] == digest({k: v for k, v in control.items() if k != 'sha256'})
            and report['requirements_sha256'] == control['sha256']
            and report['algorithm2_input_sha256'] == digest(prior),
            'invalid prior control or native package seal')
    signatures = {tuple(row[k] for k in ('target', 'schema', 'abi', 'opcode', 'completion')): row['calls']
                  for row in read(native / 'service-signatures.json')}
    require(sum(signatures.values()) == report['calls'], 'native call coverage differs')
    users, active_groups = plan_users(control, signatures)
    views = inventory_views(joint, prejoin)

    contract = read(joint / 'packet-pdma-contract.json')
    alias = read(joint / 'odb-packet-dma-net-identities.json')
    constants = check_constant_ties(joint, contract, active_groups)
    catalog = {'schema_version': 'route-contract/1', 'demands': {
        name: {'signals': [], 'requires': sorted(dep for child, dep in control['dependencies']
                                                   if child == name)}
        for name in users}}
    selected = [*control_edges(control, contract), *dma_edges(contract, users)]
    anchors = endpoint_inventory(joint)
    alias, recovered_aliases = source_aliases(prejoin, alias, selected)
    endpoints, coverage = select_endpoints(selected, catalog['demands'], alias,
                                           cut_rows(joint / 'odb-transport-open-cuts.tsv'), anchors)
    family_counts = {'descriptor': 'desc', 'weight': 'weight', 'fence': 'mc_fence'}
    for group in active_groups:
        for family, stem in family_counts.items():
            require(coverage[f'dma:{group}:{family}'] == contract['counts'][f'{group}.{stem}.live'],
                    f'incomplete physical DMA family {group}/{family}')
    require(sum(v for k, v in coverage.items() if k.startswith('packet:')) ==
            sum(len(row['sinks']) for row in control['members']),
            'control requirements projection lost physical members')

    base = {'schema_version': 'route-contract/1', 'state': 'candidate',
            'assembly_state': 'placed_parent_cuts', 'base_id': 'joint-packet-dma-placed-A',
            'dbu_per_micron': 2000, 'views': views, 'endpoints': endpoints}
    write(out / 'base.json', base)
    base = read_base(out / 'base.json')
    provenance = {
        'package_proof_sha256': source['package_proof_sha256'],
        'service_signatures_sha256': source['service_signatures_sha256'],
        'mother_targets_sha256': source['mother_targets_sha256'],
        'prior_control_request_sha256': control['sha256'],
        'joint_logical_contract_sha256': file_sha(joint / 'packet-pdma-contract.json'),
        'joint_alias_sha256': file_sha(joint / 'odb-packet-dma-net-identities.json'),
        'joint_binding_audit_sha256': file_sha(joint / 'odb-packet-dma-binding-audit.json'),
        'scope': 'native request control and P scope descriptor, weight and fence cut projection',
    }
    request = elaborate(users, catalog, base, provenance)
    verify_requirements(request, users, catalog, base, provenance)
    tech = dict(prior['technology'])
    with (joint / 'landing-obstacles.tsv').open(encoding='ascii') as stream:
        kind, _, *bounds = next(stream).split()
    require(kind == 'die' and len(bounds) == 4, 'joint placement die bounds missing')
    tech.update(bounds=list(map(int, bounds)), access_pitch=400)
    spec = bind_request(request, base, tech)
    validate(spec)
    require(all(contains(tech['bounds'], rect)
                for shapes in spec['pins'].values() for rect in shapes),
            'placed terminal outside joint die')
    missing_access = sorted(pin for pin, rects in spec['pins'].items()
                            if not access_points(rects, tech))
    program = {'source': provenance, 'kind': 'sealed_native_request_projection',
               'topology': report['topology'], 'pages': report['pages'], 'calls': report['calls'],
               'native_execution_qualified': False}
    wiring = {k: request[k] for k in ('source', 'users', 'members', 'unresolved')}
    handoff = {'route_scope': 'interface', 'status': 'interface_ready_for_algorithm_2',
               'source': provenance, 'unresolved': [], 'router_input_sha256': digest(spec),
               'program_sha256': digest(program), 'wiring_sha256': digest(wiring),
               'request_sha256': request['sha256'], 'base_sha256': request['base_sha256'],
               'coverage': {'new_signal_nets': sum(bool(row['sinks']) for row in spec['nets'])},
               'physical_qualified': False}
    for name, data in [('catalog', catalog), ('requirements', request), ('algorithm2-input', spec),
                       ('program', program), ('wiring', wiring), ('handoff', handoff)]:
        write(out / (name + '.json'), data)
    admission = verify_handoff(spec, out)
    classes = {row['odb_term']: row['anchor_class'] for row in endpoints.values()}
    result = {
        'source': provenance, 'admission': admission, 'physical_qualified': False,
        'native_execution_qualified': False, 'route_binding_scope': 'candidate interface',
        'coverage_by_bundle': dict(sorted(coverage.items())),
        'net_count': len(spec['nets']), 'terminal_count': len(spec['pins']),
        'terminal_classes': dict(Counter(classes[pin] for pin in spec['pins'])),
        'terminals_without_candidate_access': missing_access,
        'native_constant_ties': constants,
        'recovered_logical_driver_aliases': recovered_aliases,
        'algorithm2_input_sha256': file_sha(out / 'algorithm2-input.json'),
        'outstanding': ['same main P implementation and placement',
                        'lower wiring for staged parent BTerms on the joined base',
                        'remaining DMA clients, external DDR and KV read/write paths',
                        'native providers and completion compatibility', 'top clocks, reset and PG',
                        'joint upper routing and physical qualification'],
    }
    write(out / 'report.json', result)
    print(json.dumps({**result, 'native_constant_ties': len(constants),
                      'recovered_logical_driver_aliases': len(recovered_aliases),
                      'terminals_without_candidate_access': len(missing_access)}, indent=2))


if __name__ == '__main__':
    cli = argparse.ArgumentParser(description=__doc__)
    for param in ('joint', 'prejoin', 'native', 'control_dir', 'out'):
        cli.add_argument(param, type=lambda value: Path(value).resolve())
    project(**vars(cli.parse_args()))
