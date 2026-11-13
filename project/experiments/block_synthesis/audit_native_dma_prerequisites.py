"""Check the selected P stream-scope command against its real DMA interface."""
import argparse
from collections import Counter, defaultdict
from copy import deepcopy
import csv
from hashlib import sha256
import json
import re
from pathlib import Path

from route_contract import digest, read_base, require
from run import compile_event_ir


FAMILIES = {'p_dma_desc': 'descriptor', 'p_dma_weight': 'weight', 'p_dma_mc_fence': 'fence'}


def read(path):
    return json.loads(path.read_bytes())


def port_rows(path, expected_sha):
    data = path.read_bytes()
    require(sha256(data).hexdigest() == expected_sha, 'physical endpoint audit changed')
    return {row['logical_pin']: row for row in csv.DictReader(data.decode().splitlines(), delimiter='\t')}


def evaluate(selected, audit, contract_path, output):
    base = read_base(selected / 'base.json')
    original = read(selected / 'compile.json')
    require(original['physical_base_sha256'] == digest(base), 'scope and physical base differ')
    evidence = read(audit / 'main-p-dma-access-report.json')
    require(base['views']['P.odb']['sha256'] == evidence['main_p_odb_sha256']
            and base['views']['P.def']['sha256'] == evidence['main_p_def_sha256'],
            'P DMA audit uses another placed P view')
    endpoints = base['endpoints']
    p_ports = port_rows(audit / 'main-p-native-access.tsv', evidence['main_p_endpoint_table_sha256'])
    dma_ports = port_rows(audit / 'dma-native-access.tsv', evidence['dma_endpoint_table_sha256'])
    aliases = {row['alias']: row['physical_anchor'] for row in evidence['main_p_aliases']}
    contract_bytes = contract_path.read_bytes()
    contract = json.loads(contract_bytes)
    scopes = {row['group']: row for row in base['native_service_routes']['targets']}
    bits = defaultdict(list)
    gaps = defaultdict(Counter)
    sample = defaultdict(dict)
    footprints = {row['id']: row for row in base['assemblies']}
    hardware = deepcopy(original['resolved_hardware'])
    for edge in contract['edges']:
        if edge['kind'] not in FAMILIES:
            continue
        src, dst = edge['source'], edge['sink']
        require((src == 'dma') != (dst == 'dma'), 'expected one DMA port')
        group = dst if src == 'dma' else src
        if group not in scopes:
            continue
        name = 'pdma:' + group + ':' + FAMILIES[edge['kind']]
        a, b = f"{src}/{edge['source_pin']}", f"{dst}/{edge['sink_pin']}"
        bits[name].append({'name': a + '->' + b, 'width': 1, 'driver': a, 'sinks': [b]})
        for role, owner, key in (('driver', src, a), ('sink', dst, b)):
            pin = key.split('/', 1)[1]
            row = (dma_ports if owner == 'dma' else p_ports)[pin]
            require(row['family'] == edge['kind']
                    and row['direction'] == {'driver': 'OUTPUT', 'sink': 'INPUT'}[role],
                    'port evidence disagrees with the logical DMA edge')
            if owner == 'dma':
                require(owner not in footprints, 'candidate already includes DMA placement')
                gaps[name]['dma_without_candidate_placement'] += 1
                if not row['boundary_rects'] and not row['leaf_shapes']:
                    gaps[name]['dma_requires_escape'] += 1
                sample[name].setdefault('dma', key)
                continue
            anchor = p_ports[aliases.get(pin, pin)]
            require(anchor['native_net'] == row['native_net'], 'P alias crosses native components')
            if not anchor['boundary_rects']:
                require(row['leaf_shapes'], 'P port lacks audited M10 access')
                gaps[name]['p_leaf_requires_group_escape'] += 1
                sample[name].setdefault('p_leaf', key)
                continue
            rects = [list(map(int, values.split()))
                     for values in re.findall(r'\{([^{}]+)\}', anchor['boundary_rects'])]
            require(rects, 'bad audited group M10 rectangle')
            dx, dy = footprints[group]['translation_dbu']
            port = group + '/' + aliases.get(pin, pin)
            endpoints[key] = {
                'assembly': group, 'odb_term': port, 'native_net': group + '/' + row['native_net'],
                'role': role,
                'm10_shapes': [{'layer': 'M10', 'object': f'{port}/M10/{i}',
                                'rect_dbu': [v + shift for v, shift in zip(rect, (dx, dy, dx, dy))]}
                               for i, rect in enumerate(rects)],
            }
    require(len(bits) == 3 * len(scopes), 'DMA edge inventory is incomplete')
    for group, row in scopes.items():
        needs = sorted(name for name in bits if name.startswith('pdma:' + group + ':'))
        require(len(row['routes']) == 1 and len(needs) == len(FAMILIES), 'unexpected P scope inventory')
        row['routes'][0]['requires'] = needs
    for name, signals in bits.items():
        hardware['nets'][name] = {'cost': len(signals), 'signals': signals}
    result = compile_event_ir(original['event_ir'], hardware, route_base=base, route_scope='interface',
                              control_fabric=hardware['event_model']['control_fabric'], emit_outputs=True)
    failure = result.get('native_dispatch_issues', {}).get('services', {})
    require(result['status'] == 'no_plan_in_bounded_search' and len(failure) == 1
            and all(name in next(iter(failure.values())) for name in bits),
            'search did not enforce the selected command data-plane requirements')
    report = {
        'source_interface_plan_sha256': original['outputs']['program']['source']['plan_sha256'],
        'base_sha256': digest(base), 'packet_dma_contract_sha256': sha256(contract_bytes).hexdigest(),
        'status': result['status'], 'native_dispatch_issues': failure,
        'demand_status': {name: {'bits': len(signals), 'unbound': gaps[name],
                                 'examples': sample[name]} for name, signals in bits.items()},
        'constant_ties_pending': len(contract['constants']),
        'scope': 'P descriptor, weight and fence transport prerequisite binding on the main candidate',
        'physical_qualified': False,
    }
    output.mkdir()
    for name, record in {'base': base, 'hardware': hardware, 'compile': result, 'report': report}.items():
        (output / (name + '.json')).write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('selected', 'audit', 'contract_path', 'output'):
        parser.add_argument(name, type=Path)
    evaluate(**vars(parser.parse_args()))
