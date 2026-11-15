"""Import model-independent control connectivity and bind it to selected dispatches."""
from collections import defaultdict
from copy import deepcopy

from event_deploy import bit_requests, demand_closure

VERSION = 'block-event-control-fabric/1'


def owner(endpoint):
    controller, separator, pin = endpoint.rpartition('/')
    if not separator or not controller or not pin:
        raise ValueError('expected an owner/port in control interface: ' + endpoint)
    return controller


def validate_fabric(fabric):
    if fabric.get('schema_version') != VERSION:
        raise ValueError('unsupported control fabric schema')
    mother, targets, bundles = fabric['mother'], fabric['targets'], fabric['bundles']
    ids = [item['target_id'] for item in targets.values()]
    if not ids or any(type(i) is not int or i < 0 for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('invalid or reused control target ID')
    controllers = {item['controller'] for item in targets.values()}
    if not mother or mother in controllers or len(controllers) != len(targets):
        raise ValueError('control fabric needs distinct mother and local controllers')
    for name, bundle in bundles.items():
        if not bundle.get('signals') or type(bundle.get('cost')) is not int or bundle['cost'] < 0:
            raise ValueError('control bundle needs signals and a nonnegative cost: ' + name)
        if not set(bundle.get('requires', ())) <= bundles.keys():
            raise ValueError('control bundle references an unknown dependency: ' + name)
        for signal in bundle['signals']:
            if type(signal['width']) is not int or signal['width'] < 1 or not signal['sinks']:
                raise ValueError('invalid control signal: ' + signal['name'])
            owner(signal['driver'])
            for pin in signal['sinks']:
                owner(pin)
    for target, item in targets.items():
        used = set(item['bundles'])
        if not used or not used <= bundles.keys():
            raise ValueError('unknown control bundle for ' + target)
        used = demand_closure(bundles, used)
        controller = item['controller']
        for role, source, destination in (('command', mother, controller), ('done', controller, mother)):
            edges = {}
            for name in used:
                for signal in bundles[name]['signals']:
                    if signal.get('role') == role:
                        edges.setdefault(owner(signal['driver']), set()).update(map(owner, signal['sinks']))
            reached, pending = {source}, [source]
            while pending:
                more = edges.get(pending.pop(), set()) - reached
                reached.update(more)
                pending.extend(more)
            if destination not in reached:
                raise ValueError(f'{target}: no declared {role} path between mother and local controller')


def qualify_endpoint_demands(hardware):
    """Preserve legal alternatives while excluding impossible static endpoint unions."""
    members, _ = bit_requests(hardware['nets'], hardware)
    claims = defaultdict(dict)
    incompatible = {tuple(sorted(pair)) for pair in hardware.get('incompatible_nets', ())}
    for member in members:
        bundle, driver = member['demand_id'], member['driver']
        terminals = [(driver, 'driver'), *((sink, 'sink') for sink in member['sinks'])]
        for pin, direction in terminals:
            claim = (direction, driver)
            for other, previous in claims[pin].items():
                if previous == claim:
                    continue
                if other == bundle:
                    raise ValueError('incompatible claims within demand ' + bundle + ' on ' + pin)
                incompatible.add(tuple(sorted((other, bundle))))
            claims[pin][bundle] = claim
    return {**hardware, 'incompatible_nets': sorted(incompatible)} if incompatible else hardware


def attach_control_fabric(hardware, fabric):
    """Add shared and per-target nets to the exact services and moves using them."""
    validate_fabric(fabric)
    resolved = deepcopy(hardware)
    spec = resolved['event_model']
    spec['control_fabric'] = deepcopy(fabric)
    nets = resolved['nets']
    for name, declaration in fabric['bundles'].items():
        if name in nets and nets[name] != declaration:
            raise ValueError('conflicting hardware declaration for control bundle ' + name)
        nets[name] = deepcopy(declaration)
    groups = resolved.setdefault('control_groups', {})
    by_site = {entry['site']: group for group, entry in groups.items()}
    if len(by_site) != len(groups):
        raise ValueError('multiple control groups claim one site')
    targets = fabric['targets']
    unassigned = (targets.keys() & resolved['sites'].keys()) - groups.keys() - by_site.keys()
    for group in sorted(unassigned):
        groups[group] = {'site': group}
        by_site[group] = group
    for group in groups.keys() & targets.keys():
        entry = groups[group]
        target_id = targets[group]['target_id']
        if entry.get('block_id', target_id) != target_id:
            raise ValueError('native target ID differs from the hardware group: ' + group)
        entry['block_id'] = target_id

    issues = {'routes': {}, 'services': {}}
    for name, route in spec['routes'].items():
        sites = route['src'], route['dst']
        owners = {by_site.get(site) for site in sites if site != 'DDR'}
        route.setdefault('transport_nets', list(route.get('nets', ())))
        missing = owners - targets.keys()
        if missing:
            missing_sites = [site for site in sites if site != 'DDR' and by_site.get(site) in missing]
            issues['routes'][name] = 'undeclared control target for sites: ' + ', '.join(sorted(set(missing_sites)))
        else:
            route['nets'] = sorted(set(route.get('nets', ())) |
                                   {net for target in owners for net in targets[target]['bundles']})
    for name, service in spec['services'].items():
        if 'finite_loop' in service:
            owners = {entry['control'] for entry in service['finite_loop']['participants'].values()}
        else:
            site = service.get('control_site')
            owners = {by_site[site]} if site in by_site else set()
        missing = owners - targets.keys()
        if not owners or missing:
            issues['services'][name] = ('undeclared control target: ' + ', '.join(sorted(missing))
                                       if missing else 'service has no declared control group for its site')
        else:
            service['nets'] = sorted(set(service.get('nets', ())) |
                                     {net for target in owners for net in targets[target]['bundles']})
    spec['logical_control_issues'] = issues
    return resolved


def control_connectivity(program, wiring, fabric):
    selected = sorted({target for row in program['mother'] if row['op'] == 'DISPATCH'
                       for target in row['targets']})
    if set(selected) != set(program['locals']) or not set(selected) <= fabric['targets'].keys():
        raise ValueError('program uses a target outside its control fabric')
    bundles = fabric['bundles']
    by_event = defaultdict(set)
    for name in bundles.keys() & wiring['users'].keys():
        for use in wiring['users'][name]:
            if 'event_id' in use:
                by_event[use['event_id'], use['task_id'], use['binding_id']].add(name)
    target_bundles = {target: demand_closure(bundles, fabric['targets'][target]['bundles']) for target in selected}
    users = defaultdict(list)
    for row in program['mother']:
        if row['op'] != 'DISPATCH':
            continue
        key = row['sequence'], row['task_id'], row['binding_id']
        actual = demand_closure(bundles, by_event[key])
        expected = set().union(*(target_bundles[target] for target in row['targets']))
        if actual != expected:
            raise ValueError('dispatch control bundles differ from its target interfaces')
        for name in expected:
            users[name].append({'event_id': key[0], 'task_id': key[1], 'binding_id': key[2]})
    members, unresolved = bit_requests(users, {'nets': bundles})
    if unresolved:
        raise ValueError('control fabric left a connection without a bit template')
    merged, sink_drivers = {}, {}
    for row in members:
        driver = row['driver']
        net = merged.setdefault(driver, {'driver': driver, 'sinks': set(), 'bundles': set()})
        for sink in row['sinks']:
            if sink_drivers.setdefault(sink, driver) != driver:
                raise ValueError('multiple control drivers on ' + sink)
        net['sinks'].update(row['sinks'])
        net['bundles'].add(row['demand_id'])
    return {'schema': 'block-event-control-connectivity/1', 'source': program['source'],
            'abi': fabric.get('abi'), 'mother': fabric['mother'], 'scope': 'logical control connectivity',
            'targets': {name: fabric['targets'][name]['target_id'] for name in selected},
            'controllers': {name: fabric['targets'][name]['controller'] for name in selected},
            'users': {name: users[name] for name in sorted(users)},
            'nets': [{**net, 'sinks': sorted(net['sinks']), 'bundles': sorted(net['bundles'])}
                     for _, net in sorted(merged.items())]}
