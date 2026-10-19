"""Read-only server analysis: explicit physical endpoint partitions, no pair expansion."""
from pathlib import Path
import collections
import gzip
import hashlib
import json

R = Path('/public/home/yuzelu/project-circuit/llm_routing_analysis')
NETS = R / 'stats/opentpu-small-v1/dedicated_v2/nets.jsonl.gz'
COMPONENTS = R / 'unknown-analysis-20261018-v2/resolved_components.jsonl.gz'


def records(path):
    with gzip.open(path, 'rt') as stream:
        for line in stream:
            yield json.loads(line)


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def norm(name):
    return name.replace('\\[', '[').replace('\\]', ']')


def add(table, key, net, items, endpoints):
    value = table.setdefault(key, {'nets': 0, 'length_dbu': 0, 'layers': {},
                                   'functions': {}, 'examples': []})
    length = net.get('length_dbu') or 0
    value['nets'] += 1
    value['length_dbu'] += length
    function = net.get('category', 'UNKNOWN')
    function = function if function in ('CLOCK', 'RESET', 'CONTROL_HANDSHAKE') else 'OTHER'
    value['functions'][function] = value['functions'].get(function, 0) + length
    for layer, stat in net.get('layers', {}).items():
        value['layers'][layer] = value['layers'].get(layer, 0) + stat['length_dbu']
    if len(value['examples']) < 3:
        value['examples'].append({'net_id': net['id'], 'name': net['name'],
                                  'length_um': length / 2000,
                                  'endpoints': [{'instance': e.get('instance'), 'pin': e.get('pin'),
                                                  'role': e.get('role'), 'group': item[0],
                                                  'evidence': item[1]}
                                                 for e, item in zip(endpoints, items)][:12]})


inferred = {}
for component in records(COMPONENTS):
    exclusive = len(component['modules']) == 1 and not any(e['kind'] == 'BTERM' for e in component['terminals'])
    label = (component['modules'][0], 'INFERRED') if exclusive else (None, 'SHARED')
    for edge in component['edges']:
        name = norm(edge['instance'])
        assert name not in inferred or inferred[name] == label
        inferred[name] = label

tables = {name: {} for name in ['classes', 'complete_pairs', 'complete_multi',
                               'partial_pairs', 'partial_multi', 'clock_reset_cross']}
total = 0
for net in records(NETS):
    if net.get('sig_type') in ('POWER', 'GROUND'):
        continue
    endpoints = [e for e in net['endpoints'] if e.get('master_type') not in ('CORE_SPACER', 'CORE_WELLTAP', 'CORE_ANTENNACELL')]
    items = []
    for endpoint in endpoints:
        group = endpoint.get('module')
        item = (('TOP_IO', 'SOURCE') if endpoint['kind'] == 'BTERM' else
                (group, 'SOURCE') if group and group != 'UNKNOWN' else
                inferred.get(norm(endpoint['instance']), (None, 'UNKNOWN')))
        items.append(item)
    groups = {g for g, ev in items if g}
    bad = any(not g for g, ev in items)
    inf = any(ev == 'INFERRED' for g, ev in items)
    if 'TOP_IO' in groups:
        category = 'TOP_INTERFACE'
    elif len(groups) >= 2:
        category = 'CROSS_PARTIAL' if bad else 'CROSS_INFERRED' if inf else 'CROSS_SOURCE'
    elif bad:
        category = 'SHARED_SUPPORT' if any(ev == 'SHARED' for g, ev in items) else 'UNRESOLVED'
    elif len(groups) == 1 and len(endpoints) >= 2:
        category = 'INTERNAL_INFERRED' if inf else 'INTERNAL_SOURCE'
    else:
        category = 'UNRESOLVED'
    add(tables['classes'], category, net, items, endpoints)
    total += net.get('length_dbu') or 0
    if len(groups) < 2 or 'TOP_IO' in groups:
        continue
    signature = ' + '.join(sorted(groups))
    if net.get('category') in ('CLOCK', 'RESET'):
        bucket = 'clock_reset_cross'
        signature = 'CLOCK_RESET_CROSS'
    else:
        bucket = ('partial_' if bad else 'complete_') + ('pairs' if len(groups) == 2 else 'multi')
    add(tables[bucket], signature, net, items, endpoints)

assert sum(z['length_dbu'] for z in tables['classes'].values()) == total
print(json.dumps({'case': 'opentpu_small', 'units': 2000, 'total_length_dbu': total,
                  'nets_sha256': digest(NETS), 'components_sha256': digest(COMPONENTS),
                  'tables': tables,
                  'method': 'Retained source takes priority; only single-module verified BUF/INV components supplement ownership. Whole physical nets counted once; known multi-module sets not expanded. CLOCK/RESET separated from other cross-group networks.'}))
