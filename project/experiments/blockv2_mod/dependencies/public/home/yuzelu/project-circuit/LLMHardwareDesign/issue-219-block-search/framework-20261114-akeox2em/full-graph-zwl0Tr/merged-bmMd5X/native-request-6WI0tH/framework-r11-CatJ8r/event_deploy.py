"""Project selected events to control commands and router endpoint requests."""
from collections import defaultdict
from functools import lru_cache
import hashlib
from heapq import heappop, heappush
import json

from verify_cover_frontier import project

DDR = 'DDR'


def digest(value):
    encoded = json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    return hashlib.sha256(encoded).hexdigest()


def demand_closure(nets, names):
    used = set(names)
    pending = list(used)
    while pending:
        more = set(nets.get(pending.pop(), {}).get('requires', ())) - used
        used.update(more)
        pending.extend(more)
    return used


def external_addresses(spec, names):
    sizes = spec['value_bytes']
    alignment = spec.get('external_alignment_bytes', 1)
    if type(alignment) is not int or alignment < 1:
        raise ValueError('invalid external byte alignment')
    declared = spec.get('external_addresses', {})
    regions = []
    addresses = {}
    for value, start in sorted(declared.items(), key=lambda entry: entry[1]):
        if type(start) is not int or start < 0 or start % alignment or value not in sizes:
            raise ValueError('invalid external address for ' + value)
        if regions and regions[-1][1] > start:
            raise ValueError('overlapping external addresses')
        end = start + sizes[value]
        addresses[value] = start
        regions.append((start, end))
    end = regions[-1][1] if regions else 0
    for value in sorted(names - addresses.keys()):
        start = ((end + alignment - 1) // alignment) * alignment
        addresses[value] = start
        end = start + sizes[value]
    capacity = spec.get('external_capacity_bytes')
    if capacity is not None and end > capacity:
        raise ValueError('selected external allocation exceeds addressable capacity')
    return addresses


def bit_requests(users, hardware):
    members, unresolved = [], []
    for net in sorted(users):
        info = hardware['nets'][net]
        signals = info.get('signals')
        if info.get('realization'):
            if signals:
                raise ValueError('native realization also declares routed signals: ' + net)
            unresolved.append({'demand_id': net, 'reason': 'needs_native_realization_binding'})
            continue
        if not signals:
            unresolved.append({'demand_id': net, 'reason': 'missing_interface_template'})
            continue
        names = set()
        for signal in signals:
            name, width = signal['name'], signal['width']
            if name in names or type(width) is not int or width < 1 or not signal['sinks']:
                raise ValueError('invalid router signal ' + net + '/' + name)
            names.add(name)
            endpoints = set()
            for bit in range(width):
                driver = signal['driver'].format(bit=bit)
                sinks = sorted(sink.format(bit=bit) for sink in signal['sinks'])
                terminals = {driver, *sinks}
                if len(terminals) != len(sinks) + 1 or terminals & endpoints:
                    raise ValueError('aliased router signal ' + net + '/' + name)
                endpoints.update(terminals)
                members.append({'id': f'{net}/{name}/{bit}', 'demand_id': net, 'signal': name,
                                'bit': bit, 'driver': driver, 'sinks': sinks})
    return members, unresolved


def loop_lease_edges(dispatches, capacity):
    """Chain each finite-loop resource slot through its previous holder's ACK."""
    slots = {resource: [(0, -1)] * count for resource, count in capacity.items()}
    edges = {}
    for row in sorted(dispatches, key=lambda item: (item['estimated_start'], item['sequence'])):
        number, start, end = row['sequence'], row['estimated_start'], row['estimated_end']
        parents = edges.setdefault(number, set())
        for resource, units in row['leases'].items():
            free = slots[resource]
            if type(units) is not int or not 0 < units <= len(free):
                raise ValueError('invalid finite-loop resource lease')
            old = [heappop(free) for _ in range(units)]
            if any(available > start for available, _ in old):
                raise ValueError('finite-loop program overbooks a resource lease')
            parents.update(holder for _, holder in old if holder >= 0)
            for _ in old:
                heappush(free, (end, number))
    return edges


def emit(tasks, hardware, covers, plan, *, physical_base_sha256=None):
    from event_native_dispatch import route_targets, service_completion, service_targets

    projected, _ = project(tasks, covers, plan)
    spec = hardware['event_model']
    phased = spec.get('timing') in ('replay', 'snapshot')
    operations = None
    if phased:
        from event_replay_plan import dependency_program

        dependencies = dependency_program(tasks, hardware, covers, plan)
        blockers = dependencies['completion_only_blockers']
        if blockers:
            raise ValueError(f'command completion cannot preserve {len(blockers)} phase dependencies; '
                             f'first: {blockers[0]}')
        operations = dependencies['operations']
    windows = spec['windows']
    placements = {entry['site']: name for name, entry in hardware.get('control_groups', {}).items()}
    selected = [event for row in plan['tasks'] for event in row['evaluation']['events']]
    external = set(spec.get('initial_backing', ()))
    external.update(event['value'] for event in selected if event['kind'] == 'move'
                    and DDR in (event['src'], event['dst']))
    addresses = external_addresses(spec, external)

    def operand(window, value):
        placement = windows[window] if window != DDR else {'site': DDR, 'offset': addresses[value]}
        return {'site': placement['site'], 'window': window, 'address': placement['offset'],
                'value': value, 'bytes': spec['value_bytes'][value]}

    users = defaultdict(list)
    records, local = [], defaultdict(list)
    task_completions = {}
    for task, row in zip(projected, plan['tasks']):
        binding = task['bindings'][0]
        stage_specs = {entry['id']: entry for entry in binding['event_stages'] if 'id' in entry}
        task_wait = {number for dependency in task['after'] for number in task_completions[dependency]}
        stage_events = {}
        task_numbers, pending_moves = [], []
        previous = task_wait
        for event in row['evaluation']['events']:
            sequence = len(records)
            stage_id = event.get('stage_id')
            wait = set(previous if stage_id is None else task_wait)
            if stage_id is not None:
                wait.update(stage_events[parent] for parent in stage_specs[stage_id].get('after', ()))
            if phased:
                wait = {operation for operation, _ in operations[sequence]['phases'][0]['wait_for']}
            common = {'sequence': sequence, 'task_id': row['id'], 'binding_id': row['binding'],
                      'estimated_start': event['start'], 'estimated_end': event['end']}
            leases = {}
            if event['kind'] == 'move':
                src, dst = operand(event['src'], event['value']), operand(event['dst'], event['value'])
                route_name = event['route']
                route = spec['routes'][route_name]
                net_ids = route.get('nets', ())
                participants = {target: [] for target in sorted(route_targets(route, placements))}
                for operand_, role in ((src, 'send'), (dst, 'receive')):
                    source_site = operand_['site']
                    if source_site != DDR:
                        participants[placements.get(source_site, source_site)].append(role)
                read, write = [src], [dst]
                descriptor = {'op': 'COPY', 'route': route_name, 'read': read, 'write': write,
                              'required_completion': 'destination_commit_ack'}
                if event.get('materializes_output'):
                    previous = {sequence}
                else:
                    pending_moves.append(sequence)
            else:
                service_name = event['service']
                service = spec['services'][service_name]
                net_ids = service.get('nets', ())
                reads = [operand(window, value) for window, value in event['inputs'].items()]
                writes = [operand(window, value) for window, value in event['outputs'].items()]
                site = service.get('control_site', (reads or writes or [{'site': row['site']}])[0]['site'])
                if site not in hardware['sites']:
                    raise ValueError('unknown service control site ' + site)
                targets = service_targets(service, placements) or {placements.get(site, site)}
                participants = {target: ['execute'] for target in sorted(targets)}
                read, write = reads, writes
                descriptor = {'op': 'EXEC', 'service': service_name, 'read': read, 'write': write,
                              'required_completion': service_completion(service)}
                if not phased:
                    wait.update(pending_moves)
                if 'finite_loop' in service:
                    loop = service['finite_loop']
                    descriptor.update(op='RUN_LOOP', loop=loop)
                    leases = {'leases': service['claims']}
                if 'indexed_read' in service:
                    index = service['indexed_read']
                    table_address = addresses[index['table']]
                    if table_address % 16 or table_address + spec['value_bytes'][index['table']] > 1 << index['address_bits']:
                        raise ValueError('indexed table lies outside its declared address width or alignment')
                    descriptor.update(op='INDEXED_LOAD', indexed_read={**index,'table_address':table_address})
                    if 'index_window_offset' in index:
                        # The physical operand has a subwindow address. Keep the
                        # enclosing SRAM window for the command hazard check.
                        descriptor['read'] = [{**reads[0], 'address': reads[0]['address'] + index['index_window_offset']}]
                pending_moves.clear()
                previous = {sequence}
                if stage_id is not None:
                    stage_events[stage_id] = sequence
            for target, roles in participants.items():
                command = {**common, **descriptor, 'roles': roles}
                if command['op'] == 'RUN_LOOP' and 'memory_by_site' in service:
                    site = hardware['control_groups'][target]['site']
                    command['external_memory'] = service['memory_by_site'].get(site, {})
                local[target].append(command)
            records.append({**common, 'op': 'DISPATCH', 'targets': sorted(participants),
                            'wait_for': wait, 'read': read, 'write': write, **leases})
            task_numbers.append(sequence)
            for net in net_ids:
                users[net].append({'task_id': row['id'], 'binding_id': row['binding'],
                                   'event_id': sequence})
        for net in set(binding['nets']):
            users[net].append({'task_id': row['id'], 'binding_id': row['binding']})
        task_completions[row['id']] = task_numbers
    nets = hardware['nets']
    selected = demand_closure(nets, users)
    if plan['nets'] not in (sorted(users), sorted(selected)):
        raise ValueError('program and selected network union differ')

    # Preserve finite-window lifetimes even when hardware completion order
    # differs from the estimates. Reads can share a window; writes wait for
    # earlier readers and writers, including the source side of a COPY.
    writers, readers = {}, defaultdict(set)
    ordered = [] if phased else sorted(records, key=lambda row: (row['estimated_start'],
                                                                 row['estimated_end'], row['sequence']))
    for row in ordered:
        number = row['sequence']
        for access in row['read']:
            key = (access['site'], access['address'])
            if key in writers:
                row['wait_for'].add(writers[key])
            readers[key].add(number)
        for access in row['write']:
            key = (access['site'], access['address'])
            if key in writers:
                row['wait_for'].add(writers[key])
            row['wait_for'].update(reader for reader in readers.pop(key, ()) if reader != number)
            writers[key] = number

    loop_edges = loop_lease_edges([row for row in records if 'leases' in row], hardware['resources'])
    for row in records:
        row['wait_for'].update(loop_edges.get(row['sequence'], ()))
        row['wait_for'] = sorted(row['wait_for'])
        del row['read'], row['write']
    source = {'plan_sha256': digest(plan), 'hardware_sha256': digest(hardware),
              'topology_id': hardware.get('topology_id')}
    if physical_base_sha256 is not None:
        source['physical_base_sha256'] = physical_base_sha256
    dependencies = [list(edge) for edge in sorted(
        {(name, dependency) for name in selected for dependency in nets[name].get('requires', ())})]
    members, unresolved = bit_requests(selected, hardware)
    program = {'schema': 'block-event-control/1', 'source': source, 'mother': records + [
            {'op': 'END', 'wait_for': [row['sequence'] for row in records]}],
            'locals': dict(local), 'external_addresses': addresses}
    if 'native_loop_library' in spec:
        program['native_loop_library'] = spec['native_loop_library']
    outputs = {
        'program': program,
        'wiring': {'schema': 'block-event-demands/1', 'source': source, 'users': dict(users),
                   'dependencies': dependencies, 'members': members, 'unresolved': unresolved,
                   'status': 'unbound' if unresolved else 'logical_endpoints_complete'},
    }
    if 'control_fabric' in spec:
        from event_control_fabric import control_connectivity

        outputs['control_connectivity'] = control_connectivity(program, outputs['wiring'], spec['control_fabric'])
    return outputs



def attach_route_catalog(hardware, catalog):
    """Apply physical declarations without replacing the search cost model."""
    if catalog.get('schema_version') != 'route-contract/1':
        raise ValueError('unsupported route catalog schema')
    control = hardware.get('event_model', {}).get('control_fabric', {}).get('bundles', {})
    nets = {}
    for name, info in hardware['nets'].items():
        template = catalog['demands'].get(name, {})
        fields = {field: template[field] for field in ('signals', 'requires', 'realization') if field in template}
        if name in control:
            if any(value != info.get(field, [] if field == 'requires' else None)
                   for field, value in fields.items()):
                raise ValueError('route catalog changes the declared control bundle: ' + name)
            nets[name] = info
        else:
            if any(field in info and value != info[field] for field, value in fields.items()):
                raise ValueError('route catalog conflicts with hardware declaration: ' + name)
            nets[name] = {**info, **fields}
    return {**hardware, 'nets': nets}


def route_catalog(hardware):
    catalog = {'schema_version': 'route-contract/1', 'demands': {}}
    for name, info in hardware['nets'].items():
        if info.get('signals') or info.get('realization') or info.get('requires'):
            catalog['demands'][name] = {field: info[field] for field in
                                       ('signals', 'requires', 'realization') if field in info}
    return catalog


def fixed_connections_present(request, hardware, base):
    pins = base['endpoints']
    return all(all(pins[sink]['native_net'] == pins[member['driver']]['native_net'] for sink in member['sinks'])
               for member in request['members'] if hardware['nets'][member['demand_id']].get('fixed'))


def route_admission(hardware, base, contract, *, product=False):
    """Memoize static endpoint feasibility over the selected bundle union."""
    catalog = route_catalog(hardware)

    @lru_cache(maxsize=8192)
    def admitted(nets):
        try:
            request = contract.elaborate(dict.fromkeys(nets, []), catalog, base, {})
        except ValueError as exc:
            if str(exc) in ('multiple drivers on native component', 'physical endpoint direction mismatch'):
                return False
            raise
        return (request['status'] == 'endpoint_binding_complete'
                and (not product or fixed_connections_present(request, hardware, base)))

    return admitted


def bind_routes(wiring, hardware, base, elaborate, verify=None, *, catalog=None):
    """Hand a selected event graph to the existing route-contract elaborator."""
    if wiring.get('schema') != 'block-event-demands/1' or wiring['source']['hardware_sha256'] != digest(hardware):
        raise ValueError('router input is not bound to this selected event hardware')
    if 'physical_base_sha256' in wiring['source'] and wiring['source']['physical_base_sha256'] != digest(base):
        raise ValueError('router input is not bound to this physical base')
    if catalog is None:
        catalog = route_catalog(hardware)
    request = elaborate(wiring['users'], catalog, base, wiring['source'])
    if request['members'] != wiring['members'] or request['dependencies'] != wiring['dependencies']:
        raise ValueError('router expansion differs from selected event endpoint demands')
    if verify is not None:
        verify(request, wiring['users'], catalog, base, wiring['source'])
    return request


def handoff(result, hardware, base, contract, adapter, rules, validate, *, wire_budget=None):
    """Recheck the source schedule and reconstruct both outputs before binding."""
    from verify_cover_frontier import verify

    if result.get('physical_base_sha256') != digest(base):
        raise ValueError('physical base differs from the one used for mapping')
    scope = result.get('route_scope')
    if scope == 'product':
        from event_physical_contract import qualify_hardware

        if qualify_hardware(hardware, base) != hardware:
            raise ValueError('product handoff lacks derived physical interface requirements')
    elif scope != 'interface':
        raise ValueError('compile against a physical handoff target before exporting')
    event_ir, plan = result['event_ir'], result['plan']
    tasks, covers = event_ir['tasks'], event_ir.get('covers', ())
    verify(tasks, hardware, covers, plan, wire_budget=wire_budget)
    expected = emit(tasks, hardware, covers, plan, physical_base_sha256=result['physical_base_sha256'])
    program, wiring = (result['outputs'][name] for name in ('program', 'wiring'))
    if digest(program) != digest(expected['program']):
        raise ValueError('control program differs from verified event plan')
    if digest(wiring) != digest(expected['wiring']):
        raise ValueError('connection demands differ from verified event plan')
    if digest(result['outputs'].get('control_connectivity')) != digest(expected.get('control_connectivity')):
        raise ValueError('control connectivity differs from verified event plan')
    dispatches = sum(row['op'] == 'DISPATCH' for row in program['mother'])
    request = bind_routes(wiring, hardware, base, contract.elaborate, contract.verify_requirements)
    router_input = None
    if request['status'] == 'endpoint_binding_complete':
        if scope == 'product' and not fixed_connections_present(request, hardware, base):
            raise ValueError('declared fixed connection lacks actual base continuity')
        router_input = adapter.bind_request(request, base, rules['technology'], rules.get('obstacles', []))
        validate(router_input)
    ready = 'ready_for_algorithm_2' if scope == 'product' else 'interface_ready_for_algorithm_2'
    result = {'status': ready if router_input is not None else 'unbound', 'route_scope': scope,
              'source': program['source'], 'program_sha256': digest(program), 'wiring_sha256': digest(wiring),
              'request_sha256': request['sha256'], 'base_sha256': request['base_sha256'],
              'router_input_sha256': digest(router_input) if router_input is not None else None,
              'coverage': {
                  'base_state': base['state'],
                  'dispatches': dispatches,
                  'declared_demands': len(request['users']),
                  'new_signal_nets': sum(bool(set(net['sinks']) - set(net['fixed_sinks']))
                                         for net in request['nets']),
                  'native_services': sum(item['kind'] == 'native_service'
                                         for item in request.get('realizations', ())),
                  'external_boundaries': sum(item['kind'] == 'external_boundary'
                                             for item in request.get('realizations', ())),
              },
              'unresolved': request['unresolved']}
    if 'control_connectivity' in expected:
        result['control_connectivity_sha256'] = digest(expected['control_connectivity'])
    return result, request, router_input
