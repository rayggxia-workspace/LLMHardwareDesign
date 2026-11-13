"""Bind candidate command providers to the dispatch routes of the target base."""

from copy import deepcopy


def service_completion(service):
    if 'finite_loop' in service:
        return service['finite_loop']['completion']
    if 'indexed_read' in service:
        return 'destination_commit_ack'
    return 'service_done'


def route_targets(route, by_site):
    return {by_site.get(route[direction], route[direction])
            for direction in ('src', 'dst') if route[direction] != 'DDR'}


def service_targets(service, by_site):
    if 'finite_loop' in service:
        return {item['control'] for item in service['finite_loop']['participants'].values()}
    site = service.get('control_site')
    return {by_site.get(site, site)} if site is not None else set()


def signature(fields):
    key = tuple(fields[name] for name in ('schema', 'abi', 'opcode'))
    if any(type(value) is not int or not 0 < value < limit
           for value, limit in zip(key, (1 << 32, 1 << 32, 1 << 16))):
        raise ValueError('invalid native dispatch signature')
    return key


def qualify_native_dispatch(hardware, base):
    """Reject model-only providers before the schedule and wiring are selected."""
    resolved = deepcopy(hardware)
    spec = resolved['event_model']
    groups = resolved.get('control_groups', {})
    by_site = {group['site']: name for name, group in groups.items()}
    fabric = spec.get('control_fabric', {}).get('targets', {})
    assemblies = {row['id']: row for row in base.get('assemblies', ())}
    inventory = base.get('native_service_routes')
    contracts = resolved.get('native_provider_contracts', {})
    available = {}
    demands = hardware['nets']
    bound_demands = {}
    catalog = None
    rejected = {}
    if inventory is not None:
        if (inventory.get('schema') != 'native-rtl-target-routes/1'
                or inventory.get('topology_id') != resolved.get('topology_id')
                or type(inventory.get('topology_id')) is not int
                or not 0 < inventory['topology_id'] < 1 << 32):
            raise ValueError('native dispatch inventory has a different schema or topology')
        for target in inventory['targets']:
            name, number = target['group'], target['id']
            group = groups.get(name)
            if group is None:
                # A full base inventory may contain resources outside the model's candidate pool.
                continue
            controller = fabric.get(name, {}).get('controller', name)
            assembly = assemblies.get(controller, {})
            view = target['netlist_view']
            if (name in available or type(number) is not int or not 0 <= number < 256
                    or group.get('block_id') != number or view not in base['views']
                    or assembly.get('views', {}).get('netlist') != view
                    or target['netlist_sha256'] != base['views'][view]['sha256']):
                raise ValueError(f'{name}: native dispatch inventory differs from the target assembly')
            enabled = {}
            denied = {}
            for route in target.get('rejected_routes', ()):
                key = signature(route)
                reason = route.get('reason')
                if key in denied or not isinstance(reason, str) or not reason:
                    raise ValueError(f'{name}: invalid or duplicate rejected native dispatch route')
                denied[key] = reason
            for route in target['routes']:
                key = signature(route)
                completions = route['completions']
                if (key in enabled or key in denied or not isinstance(completions, (list, tuple)) or not completions
                        or any(not isinstance(terminal, str) or not terminal for terminal in completions)):
                    raise ValueError(f'{name}: invalid or duplicate native dispatch route')
                needs = route.get('requires', ())
                if (not isinstance(needs, (list, tuple))
                        or any(not isinstance(net, str) or not net for net in needs)
                        or len(set(needs)) != len(needs)):
                    raise ValueError(f'{name}: invalid native dispatch route requirements')
                enabled[key] = frozenset(completions), frozenset(needs)
            available[name] = enabled
            rejected[name] = denied

    def missing_demands(needs):
        nonlocal catalog
        if not needs:
            return set()
        from event_deploy import route_catalog
        from route_contract import elaborate

        if catalog is None:
            catalog = route_catalog(hardware)
        missing = set()
        for net in sorted(needs):
            if net not in bound_demands:
                bound_demands[net] = (net in demands and elaborate(
                    {net: []}, catalog, base, {})['status'] == 'endpoint_binding_complete')
            if not bound_demands[net]:
                missing.add(net)
        return missing

    def check(record, targets, completion):
        from event_deploy import demand_closure

        needs = set()
        if not targets:
            return 'no native command target'
        for name in sorted(targets):
            if name not in available:
                return f'{name}: missing physical service route inventory'
            provider = record.get('native_providers', {}).get(name)
            contract = contracts.get(provider)
            if contract is None:
                return f'{name}: missing native encoder contract for {provider!r}'
            calls = contract['calls']
            if not calls:
                return f'{name}: native encoder declares no calls for {provider!r}'
            required = {signature(call) for call in calls}
            denied = required & rejected[name].keys()
            if denied:
                key = min(denied)
                return f'{name}: rejected native signature {key}: {rejected[name][key]}'
            missing = required - available[name].keys()
            if missing:
                return f'{name}: no physical service route for signatures {sorted(missing)}'
            for call in calls:
                key = signature(call)
                completions, prerequisites = available[name][key]
                if call['completion'] not in completions:
                    return f'{name}: no physical completion {call["completion"]!r} for {key}'
                needs.update(prerequisites)
            if calls[-1]['completion'] != completion:
                return f'{name}: final native call does not provide {completion!r}'
        missing = missing_demands(needs)
        if missing:
            return f'missing physical native dispatch demands {sorted(missing)}'
        if needs and needs - demand_closure(demands, record.get('nets', ())):
            # A selected provider must emit its auxiliary data-plane connections
            # as part of the same plan; make them actual search requirements.
            record['nets'] = sorted(set(record.get('nets', ())) | needs)
        return None

    issues = {'routes': {}, 'services': {}}
    for name, route in spec['routes'].items():
        issue = check(route, route_targets(route, by_site), 'destination_commit_ack')
        if issue:
            issues['routes'][name] = issue
    for name, service in spec['services'].items():
        issue = check(service, service_targets(service, by_site), service_completion(service))
        if issue:
            issues['services'][name] = issue
    spec['native_dispatch_issues'] = issues
    return resolved
