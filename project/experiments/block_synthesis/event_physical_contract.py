"""Qualify transport and dispatch interfaces before product mapping."""
from copy import deepcopy
from functools import lru_cache

from event_deploy import demand_closure

TRANSPORT_ROLES = {
    'ready-valid-commit': {'data', 'valid', 'ready', 'ack'},
    'u-stored-link': {'data', 'valid', 'ready', 'stored_ack', 'address', 'ack_ready',
                      'reserved', 'reserved_address'},
}


def stage_is_local(windows, service, stage):
    """Direct operand windows belong to the controller executing the service."""
    return all(windows[window]['site'] == service.get('control_site')
               for direction in ('inputs', 'outputs') for window in stage.get(direction, ()))


def qualify_hardware(hardware, base):
    """Derive required static nets from participating sites and transport ABIs."""
    resolved = deepcopy(hardware)
    spec = resolved['event_model']
    nets = resolved['nets']
    groups = resolved.get('control_groups', {})
    by_site = {group['site']: name for name, group in groups.items()}
    mother = resolved.get('mother_control_group', 'mother')
    fabric = spec.get('control_fabric')
    endpoints = base['endpoints']
    if len(by_site) != len(groups):
        raise ValueError('multiple physical control owners for one site')

    def check_roles(names, requirements):
        """Check every bit against the physical source/sink owners."""
        available = {role: [] for role in requirements}
        for name in sorted(demand_closure(nets, names)):
            for signal in nets.get(name, {}).get('signals', ()):
                role = signal.get('role', signal['name'])
                if role not in requirements:
                    continue
                src, dst, required_width = requirements[role]
                width = signal['width']
                if type(width) is not int or width < 1 or required_width not in (None, width):
                    continue
                drivers = set()
                sinks = set()
                for bit in range(width):
                    pin = endpoints.get(signal['driver'].format(bit=bit), {})
                    targets = [endpoints.get(sink.format(bit=bit), {}) for sink in signal['sinks']]
                    if pin.get('assembly') != src or pin.get('role') != 'driver':
                        break
                    matching = [target['native_net'] for target in targets
                                if target.get('assembly') == dst and target.get('role') == 'sink']
                    if not matching or pin['native_net'] in drivers or sinks.intersection(matching):
                        break
                    drivers.add(pin['native_net'])
                    sinks.update(matching)
                else:
                    available[role].append(drivers | sinks)
        missing = [role for role, choices in available.items() if len(choices) != 1]
        if missing:
            raise ValueError(f'missing or ambiguous physical roles {sorted(missing)}')
        components = set()
        for (pins,) in available.values():
            if pins & components:
                raise ValueError('physical signal aliases another required interface role')
            components.update(pins)

    @lru_cache(maxsize=None)
    def control_net(target):
        if fabric is not None:
            if target not in fabric['targets']:
                raise ValueError(f'{target}: no control fabric target')
            required = fabric['targets'][target]['bundles']
            for name in sorted(demand_closure(nets, required)):
                for signal in nets[name]['signals']:
                    fields = [(signal['driver'], 'driver'), *((sink, 'sink') for sink in signal['sinks'])]
                    for template, direction in fields:
                        for bit in range(signal['width']):
                            pin = template.format(bit=bit)
                            endpoint = endpoints.get(pin, {})
                            if endpoint.get('role') != direction:
                                raise ValueError(f'{target}: unbound control access endpoint {pin}')
            return frozenset(required)
        name = groups.get(target, {}).get('control_net')
        try:
            if name not in nets:
                raise ValueError('missing control_net')
            check_roles([name], {'command': (mother, target, None), 'done': (target, mother, None)})
        except ValueError as exc:
            raise ValueError(f'{target}: mother/local interface: {exc}') from exc
        return frozenset({name})

    def controls_for_sites(sites):
        controls = set()
        for site in sites:
            if site == 'DDR':
                continue
            if site not in by_site:
                raise ValueError(f'{site}: missing physical control group')
            controls.update(control_net(by_site[site]))
        return controls

    def transport(profile, names, src, dst, data_width):
        required = TRANSPORT_ROLES.get(profile)
        if required is None:
            raise ValueError('missing qualified transport ABI')
        if not src or not dst or type(data_width) is not int or data_width < 8 or data_width % 8:
            raise ValueError('missing transport endpoint owner or data width')
        widths = {'data': data_width, 'address': 10, 'reserved_address': 10}
        if profile == 'u-stored-link' and data_width != 128:
            raise ValueError('U stored link requires its 128-bit data interface')
        reverse = {'ready', 'ack', 'stored_ack', 'reserved', 'reserved_address'}
        check_roles(names, {role: (dst, src, widths.get(role, 1)) if role in reverse
                            else (src, dst, widths.get(role, 1)) for role in required})

    issues = {'routes': {}, 'services': {}}
    for name, route in spec['routes'].items():
        sites = route['src'], route['dst']
        data_nets = route.get('transport_nets', route.get('nets', ()))
        try:
            if sites[0] != sites[1]:
                owners = route.get('transport_owners')
                if owners is None:
                    owners = [route.get('external_owner') if site == 'DDR' else by_site.get(site)
                              for site in sites]
                if (not isinstance(owners, (list, tuple)) or len(owners) != 2
                        or any(not isinstance(owner, str) or not owner for owner in owners)):
                    raise ValueError('missing or invalid transport endpoint owners')
                source, target = owners
                width = route.get('transport_width_bits')
                transport(route.get('transport_abi'), data_nets, source, target, width)
                if route['bytes_per_tick'] * 8 > width:
                    raise ValueError('transfer rate exceeds the declared physical data width')
            controls = controls_for_sites(sites)
        except ValueError as exc:
            issues['routes'][name] = str(exc)
        else:
            route['transport_nets'] = list(data_nets)
            route['nets'] = sorted(set(route.get('nets', ())) | controls)

    for name, service in spec['services'].items():
        try:
            if 'finite_loop' in service:
                controls = set().union(*(control_net(info['control'])
                                         for info in service['finite_loop']['participants'].values()))
                if not controls:
                    raise ValueError('finite loop has no physical control group')
            elif service.get('copy_sites'):
                raise ValueError('cross-site service requires explicit COPY control and completion')
            else:
                controls = controls_for_sites([service.get('control_site')])
            if service.get('read_bytes') or service.get('write_bytes'):
                memory_nets = service.get('memory_nets', ())
                if not set(memory_nets) <= set(service.get('nets', ())):
                    raise ValueError('memory transport is absent from service connections')
                site = service.get('finite_loop', {}).get('io_site', service.get('control_site'))
                local = service.get('memory_local_owner', by_site.get(site))
                external = service.get('memory_owner')
                for field, source, target in (('read_bytes', external, local), ('write_bytes', local, external)):
                    if service.get(field):
                        transport(service.get('memory_abi'), memory_nets, source, target,
                                  service.get('memory_width_bits'))
        except ValueError as exc:
            issues['services'][name] = str(exc)
        else:
            service['nets'] = sorted(set(service.get('nets', ())) | controls)
    spec['physical_interface_issues'] = issues
    from event_native_dispatch import qualify_native_dispatch

    return qualify_native_dispatch(resolved, base)
