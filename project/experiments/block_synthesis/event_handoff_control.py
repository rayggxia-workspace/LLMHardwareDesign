"""Check named SRAM/DDR ownership and ACKs in native range control IR."""
from collections import defaultdict

from event_deploy import external_addresses
from event_execution import scratch_overwrites


def decode_handoff(program, hardware, lease_edges):
    spec = hardware['event_model']
    library = spec['native_loop_library']
    dispatches = program['mother'][:-1]
    finishes = {}
    task_commands = defaultdict(set)
    loops = {}
    windows = spec['windows']
    addresses = external_addresses(spec, set(spec['value_bytes']))
    by_sequence = defaultdict(dict)
    for group, commands in program['locals'].items():
        for command in commands:
            seq = command['sequence']
            if group in by_sequence[seq]:
                raise ValueError('duplicate native handoff target')
            by_sequence[seq][group] = command
    placements = {info['site']: group for group, info in hardware['control_groups'].items()}

    def operand(entry):
        value, window, site = entry['value'], entry['window'], entry['site']
        location = {'site': 'DDR', 'offset': addresses[value]} if window == 'DDR' else windows[window]
        if entry['bytes'] != spec['value_bytes'][value] or (site, entry['address']) != (
                location['site'], location['offset']):
            raise ValueError('native handoff record address differs')
        return window, value

    access, destroyed = {}, {}
    for seq, dispatch in enumerate(dispatches):
        task, binding = dispatch['task_id'], dispatch['binding_id']
        start, end = dispatch['estimated_start'], dispatch['estimated_end']
        previous = dispatch['wait_for']
        commands = by_sequence.pop(seq, {})
        if (dispatch['op'] != 'DISPATCH' or dispatch['sequence'] != seq or not commands
                or sorted(commands) != dispatch['targets'] or not start < end
                or not set(previous) <= finishes.keys()
                or any(finishes[parent] > start for parent in previous)
                or not lease_edges[seq] <= set(previous)):
            raise ValueError('invalid native handoff dispatch or ACK')
        if task not in library['dependencies']:
            raise ValueError('unknown handoff task')
        parents = set().union(*(task_commands[parent] for parent in library['dependencies'][task]))
        raw = next(iter(commands.values()))
        reads = [operand(entry) for entry in raw['read']]
        writes = [operand(entry) for entry in raw['write']]
        if raw['op'] == 'COPY':
            route = spec['routes'][raw['route']]
            if (len(reads) != 1 or len(writes) != 1 or reads[0][1] != writes[0][1]
                    or [entry['site'] for entry in raw['read'] + raw['write']] != [route['src'], route['dst']]
                    or dispatch['leases'] != route['claims'] or raw['required_completion'] != 'destination_commit_ack'):
                raise ValueError('invalid native handoff COPY')
            size = spec['value_bytes'][reads[0][1]]
            duration = (route['setup'] + (size + route['bytes_per_tick'] - 1) // route['bytes_per_tick'])
            if end - start != duration * route.get('ticks_per_word', 1):
                raise ValueError('native handoff COPY duration differs')
            roles = {placements[site]: [role] for site, role in
                     ((route['src'], 'send'), (route['dst'], 'receive')) if site != 'DDR'}
        else:
            service_id = task + '@' + binding
            service = spec['services'][service_id]
            loop = service['finite_loop']
            handoff = loop.get('sram_handoff', {'inputs': {}, 'outputs': {}})
            if (raw['op'] != 'RUN_LOOP' or raw.get('service') != service_id or raw.get('loop') != loop
                    or raw['required_completion'] != loop['completion']
                    or loop.get('range') != library['ranges'].get(task)
                    or dict(reads) != handoff['inputs'] or dict(writes) != handoff['outputs']
                    or dispatch['leases'] != service['claims'] or end - start != service['ticks']
                    or task in loops):
                raise ValueError('native handoff RUN_LOOP differs from binding')
            roles = {entry['control']: ['execute'] for entry in loop['participants'].values()}
            loops[task] = dispatch
            destroyed[seq] = scratch_overwrites(service, windows)
        if set(commands) != roles.keys():
            raise ValueError('native handoff participant mismatch')
        common = ('sequence', 'task_id', 'binding_id', 'estimated_start', 'estimated_end')
        for group, command in commands.items():
            if (any(command[field] != dispatch[field] for field in common)
                    or command['roles'] != roles[group]
                    or any(command.get(field) != raw.get(field) for field in
                           ('op', 'read', 'write', 'route', 'service', 'loop', 'required_completion'))):
                raise ValueError('native handoff participants disagree')
            if raw['op'] == 'RUN_LOOP' and command.get('external_memory') != service['memory_by_site'].get(
                    hardware['control_groups'][group]['site'], {}):
                raise ValueError('native handoff participant memory differs')
        waits = set(previous)
        for parent in previous:
            waits.update(access[parent][2])
        if (not parents <= waits
                or (raw['op'] == 'RUN_LOOP' and not task_commands[task] <= waits)
                or any(parent not in loops for parent in library['dependencies'][task])):
            raise ValueError(f'native handoff waits do not cover predecessor commands: {task}')
        access[seq] = reads, writes, waits
        finishes[seq] = end
        task_commands[task].add(seq)

    if (by_sequence or set(loops) != library['dependencies'].keys()
            or program['mother'][-1] != {'op': 'END', 'wait_for': list(finishes)}):
        raise ValueError('incomplete native handoff control')
    last_write, readers = {}, defaultdict(set)
    ordered = sorted(dispatches, key=lambda row: (row['estimated_start'], row['sequence']))
    for dispatch in ordered:
        seq = dispatch['sequence']
        reads, writes, waits = access[seq]
        for window, value in reads:
            key = (window, value if window == 'DDR' else None)
            old = last_write.get(key)
            if old is None or old[0] != value or old[1] not in waits:
                raise ValueError('native handoff read precedes committed version')
            readers[key].add(seq)
        for window in destroyed.get(seq, ()):
            key = (window, None)
            old = last_write.get(key)
            if ((old is not None and old[1] not in waits) or not readers.pop(key, set()) <= waits):
                raise ValueError('native tile overwrites a live SRAM window')
            last_write[key] = None, seq
        for window, value in writes:
            key = (window, value if window == 'DDR' else None)
            old = last_write.get(key)
            if window != 'DDR' and (old is not None and old[1] not in waits
                                    or not readers[key] <= waits):
                raise ValueError('native handoff overwrites a live SRAM window')
            readers[key].clear()
            last_write[key] = value, seq
    return [row for row in ordered if row['task_id'] in loops and row is loops[row['task_id']]]
