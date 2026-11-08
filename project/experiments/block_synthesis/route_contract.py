"""Versioned synthesis -> pin-access contract. No geometry/signoff claims.

Endpoint manifests are exported physical facts, not inferred from bundle names.
This layer never changes the search, arithmetic, placement or native wiring.
"""
import argparse
from collections import defaultdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path

VERSION = 'route-contract/1'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False).encode()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def seal(value):
    value = deepcopy(value)
    value.pop('sha256', None)
    value['sha256'] = digest(value)
    return value


def selected_demands(ir, plan):
    # Independent schedule checker includes cache leases and static conflicts.
    from verify_loop_dp import verify
    verify(ir['tasks'], ir['hardware'], plan)
    tasks = {t['id']: t for t in ir['tasks']}
    users = defaultdict(list)
    for row in plan['tasks']:
        binding = next(b for b in tasks[row['id']]['bindings'] if b['id'] == row['binding'])
        for net in set(binding['nets']):
            users[net].append({'task_id': row['id'], 'binding_id': row['binding']})
    # Unused fixed networks remain electrically present.
    for net, meta in ir['hardware']['nets'].items():
        if meta.get('fixed'):
            users.setdefault(net, [])
    return dict(users)


def u_link_catalog(connections):
    """Explicit #221 U stored_link ABI; not a generic macro-width inference.

    Reservation sideband is required even though the historical 142-bit
    transport listing omits it. Physical locations deliberately remain absent.
    """
    expected = [('data', 128, 'forward'), ('address', 10, 'forward'),
                ('valid', 1, 'forward'), ('ready', 1, 'reverse'),
                ('stored_ack', 1, 'reverse'), ('ack_ready', 1, 'forward')]
    roles = {'data': ('outgoing_data', 'incoming_data'),
             'address': ('outgoing_addr', 'incoming_addr'),
             'valid': ('outgoing_valid', 'incoming_valid'),
             'ready': ('incoming_ready', 'outgoing_ready'),
             'stored_ack': ('incoming_ack', 'outgoing_ack'),
             'ack_ready': ('outgoing_ack_ready', 'incoming_ack_ready')}
    demands = {}
    for link in connections['custom_links']:
        require([(f['name'], f['bits'], f['direction']) for f in link['fields']] == expected,
                'not the pinned U stored_link ABI')
        src, dst, name = link['src'], link['dst'], link['id']
        require(name not in demands and src != dst, 'duplicate/self U link')
        signals = []
        for field, width, direction in expected:
            a, b = (src, dst) if direction == 'forward' else (dst, src)
            output, input_ = roles[field]
            suffix = '[{bit}]' if width > 1 else ''
            signals.append({'name': field, 'width': width,
                            'driver': a+'.'+output+suffix, 'sinks': [b+'.'+input_+suffix]})
        reservation = name+'.reservation'
        demands[name] = {'signals': signals, 'requires': [reservation, 'control.distribution']}
        demands[reservation] = {'signals': [
            {'name': 'reserved', 'width': 1, 'driver': dst+'.link_rx_reserved',
             'sinks': [src+'.peer_rx_reserved']},
            {'name': 'reserved_address', 'width': 10, 'driver': dst+'.link_rx_addr[{bit}]',
             'sinks': [src+'.peer_rx_addr[{bit}]']}], 'requires': []}
    return {'schema_version': VERSION, 'profile': 'U-stored-link@17ba807d', 'demands': demands}


def expand(users, catalog):
    """Expand dependency closure and bit signals without inventing unknowns."""
    require(catalog.get('schema_version') == VERSION, 'unsupported interface schema')
    templates = catalog.get('demands', {})
    users = deepcopy(users)
    pending = list(users)
    dependencies = set()
    while pending:
        name = pending.pop()
        for dep in templates.get(name, {}).get('requires', []):
            dependencies.add((name, dep))
            if dep not in users:
                users[dep] = []
                pending.append(dep)
    members = []
    unresolved = []
    for name in sorted(users):
        template = templates.get(name)
        if not template or not template.get('signals'):
            unresolved.append({'demand_id': name, 'reason': 'missing_interface_template'})
            continue
        names = set()
        for signal in template['signals']:
            width = signal['width']
            require(type(width) is int and width > 0, 'invalid signal width')
            require(signal['name'] not in names, 'duplicate signal')
            names.add(signal['name'])
            require(signal.get('sinks'), 'signal without sink')
            for bit in range(width):
                driver = signal['driver'].format(bit=bit)
                sinks = [p.format(bit=bit) for p in signal['sinks']]
                require(len(set(sinks)) == len(sinks) and driver not in sinks, 'invalid signal terminals')
                members.append({'id': name+'/'+signal['name']+'/'+str(bit),
                                'demand_id': name, 'signal': signal['name'], 'bit': bit,
                                'driver': driver, 'sinks': sorted(sinks)})
    # Reject accidental vector broadcast caused by omitted {bit} placeholders.
    endpoints = {}
    for member in members:
        for endpoint in [member['driver']]+member['sinks']:
            key = (member['demand_id'], member['signal'], endpoint)
            require(key not in endpoints, 'bits alias within vector signal')
            endpoints[key] = member['bit']
    return users, sorted(dependencies), members, unresolved


def validate_base(base):
    require(base.get('schema_version') == VERSION, 'unsupported base schema')
    require(base.get('state') in ('candidate', 'frozen'), 'unknown base state')
    require(base.get('base_id'), 'missing base identity')
    # These are references, not a second manually maintained geometry database.
    for view in base.get('views', {}).values():
        require(view.get('path') and len(view.get('sha256', '')) == 64, 'invalid view reference')
    for pin in base.get('endpoints', {}).values():
        require(pin.get('odb_term') and pin.get('native_net'), 'missing physical terminal identity')
        require(pin.get('role') in ('driver', 'sink'), 'unknown endpoint direction')
        require(pin.get('m10_shapes'), 'missing M10 conductor reference')
        for shape in pin['m10_shapes']:
            r = shape.get('rect_dbu', [])
            require(shape.get('layer') == 'M10' and shape.get('object') and len(r) == 4
                    and all(type(v) is int for v in r) and r[0] < r[2] and r[1] < r[3],
                    'invalid M10 conductor reference')
    if base.get('endpoints'):
        require(type(base.get('dbu_per_micron')) is int and base['dbu_per_micron'] > 0,
                'missing database units')
        require(all(k in base.get('views', {}) for k in ('odb', 'netlist', 'gds')),
                'bound endpoints require ODB/netlist/GDS references')


def bind_members(members, base):
    """Canonicalize actual drivers, merge fanout and reject native shorts."""
    endpoints = base.get('endpoints', {})
    claims = {}
    nets = {}
    unresolved = []
    # Exporter must enumerate native connected components and their driver.
    fixed = base.get('fixed_native_nets', {})
    for component, net in fixed.items():
        require(net.get('driver'), 'native component without declared driver')
        claims[component] = net['driver']
    for member in members:
        terminals = [member['driver']]+member['sinks']
        missing = [p for p in terminals if p not in endpoints]
        if missing:
            unresolved.append({'member_id': member['id'], 'reason': 'unbound_endpoint', 'endpoints': missing})
            continue
        pins = [endpoints[p] for p in terminals]
        require(pins[0]['role'] == 'driver' and all(p['role'] == 'sink' for p in pins[1:]),
                'physical endpoint direction mismatch')
        driver = pins[0]['odb_term']
        for pin in pins:
            component = pin['native_net']
            require(component not in claims or claims[component] == driver, 'multiple drivers on native component')
            claims[component] = driver
        key = 'net-'+digest(driver)[:24]
        net = nets.setdefault(key, {'id': key, 'driver': driver, 'sinks': [], 'members': [],
                                   'fixed_sinks': [], 'status': 'bound_geometry_unchecked'})
        net['members'].append(member['id'])
        for pin in pins[1:]:
            if pin['odb_term'] not in net['sinks']:
                net['sinks'].append(pin['odb_term'])
            if pin['native_net'] == pins[0]['native_net']:
                net['fixed_sinks'].append(pin['odb_term'])
    for net in nets.values():
        for key in ('sinks', 'members', 'fixed_sinks'):
            net[key] = sorted(set(net[key]))
    return sorted(nets.values(), key=lambda n: n['id']), unresolved


def elaborate(users, catalog, base, source):
    validate_base(base)
    users, dependencies, members, unresolved = expand(users, catalog)
    nets, missing = bind_members(members, base)
    result = {'schema_version': VERSION, 'source': source,
              'base_id': base['base_id'], 'base_sha256': digest(base),
              'catalog_sha256': digest(catalog), 'users': users,
              'dependencies': [list(d) for d in dependencies], 'members': members,
              'nets': nets, 'unresolved': unresolved+missing,
              'status': 'unbound' if unresolved or missing else 'endpoint_binding_complete',
              'physical_qualified': False,
              'scope': 'manifest binding only; no via access, geometry, RC, STA or system qualification'}
    return seal(result)


def from_plan(ir, plan, catalog, base):
    return elaborate(selected_demands(ir, plan), catalog, base,
                     {'ir_sha256': digest(ir), 'plan_sha256': digest(plan)})


def read_base(path):
    """Check referenced bytes; this is not an ODB/GDS connectivity audit."""
    base = json.loads(path.read_text(encoding='utf-8'))
    validate_base(base)
    for view in base.get('views', {}).values():
        artifact = Path(view['path'])
        if not artifact.is_absolute():
            artifact = path.parent/artifact
        h = hashlib.sha256()
        with artifact.open('rb') as stream:
            for chunk in iter(lambda: stream.read(1024*1024), b''):
                h.update(chunk)
        require(h.hexdigest() == view['sha256'], 'physical view hash differs: '+view['path'])
    return base


def verify_requirements(request, users, catalog, base, source):
    """Reconstruct contract from immutable inputs; does not trust output totals.

    Shares schema expansion with the producer (not an independent physical
    connectivity checker). Source schedule check remains verify_loop_dp.
    """
    require(request == elaborate(users, catalog, base, source), 'route request differs from source reconstruction')
    # Separate terminal-level coverage accounting, not producer totals.
    actual = {m['id']: m for m in request['members']}
    require(len(actual) == len(request['members']), 'duplicate bit member')
    expected = set()
    for name in request['users']:
        template = catalog.get('demands', {}).get(name, {})
        for signal in template.get('signals', []):
            for bit in range(signal['width']):
                key = name+'/'+signal['name']+'/'+str(bit)
                expected.add(key)
                member = actual.get(key, {})
                require(member.get('driver') == signal['driver'].format(bit=bit) and
                        member.get('sinks') == sorted(p.format(bit=bit) for p in signal['sinks']),
                        'incorrect bit terminal coverage')
    require(set(actual) == expected, 'bit coverage differs')
    bound = {m['id'] for m in request['members']
             if all(p in base.get('endpoints', {}) for p in [m['driver']]+m['sinks'])}
    routed = [key for net in request['nets'] for key in net['members']]
    require(len(routed) == len(set(routed)) and set(routed) == bound, 'physical member coverage differs')
    return {'passed': True, 'physical_qualified': False}


def feedback(request, observations):
    require(request == seal(request), 'corrupted request digest')
    allowed = {'search_not_found', 'geometry_failed', 'electrical_failed',
               'timing_failed', 'contract_invalid'}
    member_ids = {m['id'] for m in request['members']}
    net_ids = {n['id'] for n in request['nets']}
    output = []
    for row in observations:
        require(row['category'] in allowed, 'unknown feedback category')
        require(set(row.get('member_ids', [])) <= member_ids and
                set(row.get('net_ids', [])) <= net_ids, 'foreign feedback target')
        require(row.get('member_ids') or row.get('net_ids'), 'feedback without target')
        require(row.get('code') and row.get('evidence'), 'feedback without code/evidence')
        require(row.get('phase') in ('binding', 'access', 'routing', 'geometry', 'electrical', 'timing'),
                'unknown feedback phase')
        require(not row.get('hard_constraint'), 'v1 does not import unverified hard pruning proofs')
        output.append({**row, 'hard_constraint': False})
    return seal({'schema_version': VERSION, 'base_id': request['base_id'],
                 'base_sha256': request['base_sha256'], 'request_sha256': request['sha256'],
                 'observations': output, 'physical_qualified': False})


def verify_feedback(value, request):
    require(value == seal(value), 'corrupted feedback digest')
    require(value['request_sha256'] == request['sha256'] and
            value['base_sha256'] == request['base_sha256'] and value['base_id'] == request['base_id'],
            'stale feedback context')
    require(value == feedback(request, value['observations']), 'invalid feedback')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ir', type=Path)
    p.add_argument('--plan', type=Path)
    p.add_argument('--u-connections', type=Path)
    p.add_argument('--catalog', type=Path)
    p.add_argument('--base', type=Path)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--require-bound', action='store_true')
    a = p.parse_args()
    read = lambda f: json.loads(f.read_text(encoding='utf-8'))
    base = read_base(a.base) if a.base else {'schema_version': VERSION, 'base_id': 'unbound',
                                      'state': 'candidate', 'endpoints': {}}
    if a.u_connections:
        require(not a.ir and not a.plan and not a.catalog, 'choose plan or pinned U ABI input')
        connections = read(a.u_connections)
        catalog = u_link_catalog(connections)
        users = {n: [] for n in connections['all_plan_demands']}
        source = {'connections_sha256': digest(connections)}
        request = elaborate(users, catalog, base, source)
    else:
        require(a.ir and a.plan, 'both IR and plan are required')
        ir, plan = read(a.ir), read(a.plan)
        catalog = read(a.catalog) if a.catalog else {'schema_version': VERSION, 'demands': {}}
        users = selected_demands(ir, plan)
        source = {'ir_sha256': digest(ir), 'plan_sha256': digest(plan)}
        request = elaborate(users, catalog, base, source)
    verify_requirements(request, users, catalog, base, source)
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(request, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'status': request['status'], 'members': len(request['members']),
                      'unresolved': len(request['unresolved']), 'physical_qualified': False}))
    if a.require_bound and request['status'] != 'endpoint_binding_complete':
        raise SystemExit(2)


if __name__ == '__main__':
    main()
