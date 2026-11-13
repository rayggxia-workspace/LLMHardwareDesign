"""Independent resource inventory and logical-to-physical topology checks."""
import math
from copy import deepcopy

from check import digest, verify
from geometry import contains, need, touching, validate


def rect(value):
    return (isinstance(value, list) and len(value) == 4
            and all(type(x) is int for x in value)
            and value[0] < value[2] and value[1] < value[3])


def number(value):
    return type(value) in (int, float) and math.isfinite(value) and value >= 0


def inventory(spec, data):
    validate(spec)
    need(data.get('schema_version') == 'upper-repeaters/1' and data.get('units') == spec['units'],
         'unsupported repeater inventory or units')
    if 'dbu_per_micron' in spec.get('context', {}):
        need(data.get('dbu_per_micron') == spec['context']['dbu_per_micron'], 'repeater DBU scale differs')
    bounds = spec['technology']['bounds']
    fixed = data.get('native_keepouts', [])
    need(all(rect(r) for r in fixed), 'invalid native keepout')
    pins = dict(spec['pins'])
    relay_pins = []
    resources = {}
    footprints = []
    electrical = data.get('electrical', {})
    for key in ('wire_cap_ff_per_dbu', 'via10_cap_ff', 'via11_cap_ff', 'repeater_penalty_dbu'):
        need(number(electrical.get(key, 0)), 'invalid electrical coefficient: '+key)
    for relay in data['repeaters']:
        name = relay['id']
        need(isinstance(name, str) and name and name not in resources, 'duplicate or invalid repeater id')
        state = relay['status']
        need(state in ('virtual', 'physical'), 'invalid repeater status')
        need(relay.get('power') == ('verified' if state == 'physical' else 'assumed'),
             'repeater power declaration missing')
        if state == 'physical':
            checksum = relay.get('native_view_sha256', '')
            need(isinstance(checksum, str) and len(checksum) == 64
                 and all(c in '0123456789abcdef' for c in checksum), 'physical repeater lacks native view identity')
        footprint = relay['footprint_dbu']
        need(rect(footprint) and contains(bounds, footprint), 'invalid repeater footprint')
        need(not any(touching(footprint, r) and min(r[2], footprint[2]) > max(r[0], footprint[0])
                     and min(r[3], footprint[3]) > max(r[1], footprint[1]) for r in [*fixed, *footprints]),
             'repeater footprint overlap')
        footprints.append(footprint)
        for port in ('input', 'output'):
            pin = relay[port]
            name_pin = pin['id']
            shapes = pin['m10']
            need(isinstance(name_pin, str) and name_pin and name_pin not in pins, 'duplicate repeater pin')
            need(shapes and all(rect(r) and contains(bounds, r) for r in shapes), 'invalid repeater M10 shape')
            need(not any(touching(a, b) for a in shapes for b in relay_pins), 'repeater M10 short')
            need(not any(touching(a, b) for a in shapes for rs in spec['pins'].values() for b in rs),
                 'repeater M10 overlaps native pin')
            relay_pins.extend(shapes)
            pins[name_pin] = shapes
        need(number(relay.get('input_cap_ff', 0)) and number(relay.get('output_limit_ff', 0)),
             'invalid repeater electrical model')
        resources[name] = relay
    for key in ('sink_caps_ff', 'driver_limits_ff'):
        for pin, value in electrical.get(key, {}).items():
            need(pin in spec['pins'] and number(value), 'invalid original pin electrical value')
    return pins, resources


def allocation_chain(allocation):
    if allocation is None:
        return []
    if 'repeater' in allocation:
        need(set(allocation) == {'repeater', 'sinks'}, 'invalid single repeater allocation')
        return [allocation['repeater']]
    need(set(allocation) == {'chain', 'sinks'} and isinstance(allocation['chain'], list)
         and len(allocation['chain']) > 1, 'invalid repeater chain')
    return allocation['chain']


def physical_nets(net, index, allocation, resources):
    """Each stage has an actual driver. All original sinks appear exactly once."""
    chain = allocation_chain(allocation)
    root = 'segment/%d/0' % index
    if not chain:
        return [{'id': root, 'driver': net['driver'], 'sinks': net['sinks']}]
    sinks = allocation['sinks']
    need(isinstance(sinks, list) and sinks and len(set(sinks)) == len(sinks)
         and set(sinks) <= set(net['sinks']), 'invalid repeater branch sinks')
    stages = []
    driver = net['driver']
    direct = [p for p in net['sinks'] if p not in sinks]
    for stage, relay in enumerate(resources[r] for r in chain):
        stages.append({'id': 'segment/%d/%d' % (index, stage), 'driver': driver,
                       'sinks': direct + [relay['input']['id']]})
        driver = relay['output']['id']
        direct = []
    stages.append({'id': 'segment/%d/%d' % (index, len(chain)), 'driver': driver, 'sinks': sinks})
    return stages


def projection(spec, data, allocations, failed):
    pins, resources = inventory(spec, data)
    logical = {n['id']: n for n in spec['nets']}
    need(set(allocations).isdisjoint(failed) and set(allocations) | set(failed) == set(logical),
         'logical net coverage differs')
    used = set()
    nets = []
    for index, name in enumerate(sorted(logical)):
        allocation = allocations.get(name)
        for relay in allocation_chain(allocation):
            need(relay in resources and relay not in used, 'unknown or shared repeater')
            used.add(relay)
        nets.extend(physical_nets(logical[name], index, allocation, resources))
    obstacles = deepcopy(spec.get('obstacles', []))
    for relay in resources.values():
        obstacles.extend(deepcopy(relay.get('obstacles', [])))
    return {**{key: value for key, value in spec.items() if key != 'bundles'},
            'pins': pins, 'nets': nets, 'obstacles': obstacles,
            'context': {**spec.get('context', {}), 'logical_spec_sha256': digest(spec),
                        'repeaters_sha256': digest(data)}}


def check_allocations(spec, data, result):
    need(result.get('schema_version') == 'upper-repeater-result/1', 'unsupported repeater result')
    allocations = result['allocations']
    failed = result['failed']
    physical = projection(spec, data, allocations, failed)
    need(physical == result['physical_spec'], 'physical topology differs from logical projection')
    routes = result['physical_routes']
    expected_failed = {'segment/%d/0' % i: failed[name]
                       for i, name in enumerate(sorted(n['id'] for n in spec['nets'])) if name in failed}
    need(routes['failed'] == expected_failed, 'failed segment does not match its logical net')
    states = {r['id']: r['status'] for r in data['repeaters']}
    virtual = sorted(r for a in allocations.values() for r in allocation_chain(a) if states[r] == 'virtual')
    need(result['used_virtual'] == virtual and result['physical_qualified'] is False,
         'invalid scope or physical qualification')
    checked = verify(physical, routes)
    need(result['status'] == ('partial' if failed else 'geometry_complete'), 'false completion')
    return {**checked, 'logical_nets_checked': len(allocations), 'used_virtual': virtual}
